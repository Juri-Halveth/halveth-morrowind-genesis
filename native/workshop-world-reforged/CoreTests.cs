using System;
using System.IO;
using System.Text;
using System.Linq;
using System.Collections.Generic;
namespace Halveth.Morrowind {
 static class CoreTests {
  static int checks=0; static List<string> passed=new List<string>();
  static void Check(bool valid,string label){if(!valid)throw new Exception(label);checks++;passed.Add(label);}
  static void Reject(Action action,string label){try{action();}catch(InvalidDataException){checks++;passed.Add(label);return;}throw new Exception("Not rejected: "+label);}
  static void Sub(BinaryWriter w,string tag,byte[] data){w.Write(Encoding.ASCII.GetBytes(tag));w.Write((uint)data.Length);w.Write(data);}
  static void Rec(BinaryWriter w,string tag,byte[] data){w.Write(Encoding.ASCII.GetBytes(tag));w.Write((uint)data.Length);w.Write(0);w.Write(0);w.Write(data);}
  static void MakeEsm(string file,params string[] masters){using(var f=File.Create(file))using(var w=new BinaryWriter(f)){using(var m=new MemoryStream())using(var s=new BinaryWriter(m)){Sub(s,"HEDR",new byte[300]);foreach(string master in masters){Sub(s,"MAST",Encoding.GetEncoding(1252).GetBytes(master+"\0"));Sub(s,"DATA",new byte[8]);}Rec(w,"TES3",m.ToArray());}foreach(string t in new[]{"CELL","NPC_","LAND","GMST"})Rec(w,t,new byte[0]);}}
  static void MakeBsa(string file){byte[] name=Encoding.ASCII.GetBytes("sound/test.wav\0");using(var w=new BinaryWriter(File.Create(file))){w.Write(0x100u);w.Write((uint)(12+name.Length));w.Write(1u);w.Write(4u);w.Write(0u);w.Write(0u);w.Write(name);w.Write(0UL);w.Write(new byte[]{1,2,3,4});}}
  static int Main(string[] args){string output=args[0];string temp=Path.Combine(Path.GetTempPath(),"hmw-"+Guid.NewGuid().ToString("N"));Directory.CreateDirectory(temp);
   try{
    Check(Util.Arg("one two")=="\"one two\"","Process arguments retain spaces");
    Check(Util.Arg("C:\\tail\\")=="\"C:\\tail\\\\\"","Trailing slash quoting is exact");
    Check(Util.CfgPath("C:\\x & y")=="\"C:/x && y\"","OpenMW ampersand escaping");
    foreach(string p in new[]{"../out","a/../../out","C:/out","/out","a//b","a./b","a:stream"})Reject(()=>Util.Inside(temp,p),"Path rejected: "+p);
    Reject(()=>Util.CfgPath("x\ncontent=foreign"),"Multiline config path rejected");
    string source=Path.Combine(temp,"source");Directory.CreateDirectory(source);MakeEsm(Path.Combine(source,"Morrowind.esm"));MakeBsa(Path.Combine(source,"Morrowind.bsa"));
    Check(Inspect.Tes3(Path.Combine(source,"Morrowind.esm")).Count==5,"Synthetic TES3 records inspected");
    Check(Inspect.Bsa(Path.Combine(source,"Morrowind.bsa")).Categories["sound"]==1,"BSA file range/name interpreted");
    string broken=Path.Combine(temp,"truncated.esm");File.WriteAllBytes(broken,File.ReadAllBytes(Path.Combine(source,"Morrowind.esm")).Take(320).ToArray());Reject(()=>Inspect.Tes3(broken),"Truncated TES3 rejected");
    broken=Path.Combine(temp,"range.bsa");var damaged=File.ReadAllBytes(Path.Combine(source,"Morrowind.bsa"));damaged[16]=255;File.WriteAllBytes(broken,damaged);Reject(()=>Inspect.Bsa(broken),"Out-of-range BSA rejected");
    string originalHash=Util.Hash(Path.Combine(source,"Morrowind.esm"));var w=new Workshop(Path.Combine(temp,"workshop"));var receipt=w.Import(Path.Combine(source,"Morrowind.esm"),s=>{});
    Check(receipt.Files.Count==2,"Import copies complete fixture set");Check(originalHash==Util.Hash(Path.Combine(source,"Morrowind.esm")),"Source digest unchanged after import");
    Check(Util.Hash(Path.Combine(w.DataRoot(),"Morrowind.esm"))==originalHash,"Destination equals source");
    Check(receipt.Scope.Contains("not publisher provenance"),"Structure receipt does not claim authenticity");
    MakeEsm(Path.Combine(w.DataRoot(),"adamantiumarmor.esp"),"Morrowind.esm");
    string selected=w.State.ActiveImport;File.WriteAllBytes(Path.Combine(source,"Morrowind.esm"),new byte[100]);Reject(()=>w.Import(Path.Combine(source,"Morrowind.esm"),s=>{}),"Bad source rejected before activation");Check(w.State.ActiveImport==selected,"Failed import preserves active source");
    string engine=Path.Combine(w.Root,"engine");Directory.CreateDirectory(engine);File.WriteAllText(Path.Combine(engine,"openmw.cfg"),"# synthetic engine\n",Util.Utf8);File.WriteAllBytes(Path.Combine(engine,"openmw.exe"),new byte[]{0});
    string presets=Path.Combine(w.Root,"presets");Directory.CreateDirectory(presets);File.WriteAllText(Path.Combine(presets,"world-reforged.cfg"),"[Video]\nframerate limit = 120\n",Util.Utf8);
    var extensionFiles=new List<FileReceipt>();foreach(string relative in Workshop.RequiredHalvethFiles){string file=Util.Inside(w.Root,relative);Directory.CreateDirectory(Path.GetDirectoryName(file));File.WriteAllText(file,"-- synthetic own extension\n",Util.Utf8);extensionFiles.Add(new FileReceipt{Path=relative,Bytes=new FileInfo(file).Length,Sha256=Util.Hash(file)});}Util.Write(Path.Combine(w.Root,"halveth-extension.json"),new HalvethExtensionManifest{Schema="halveth.morrowind.own-extension.v1",Files=extensionFiles,Scope="SYNTHETIC_TEST_ONLY"});
    string basePatch=Path.Combine(temp,"world-reforged-base");Directory.CreateDirectory(Path.Combine(basePatch,"shaders"));MakeEsm(Path.Combine(basePatch,"LUCINET-World-Reforged.esp"),"Morrowind.esm");File.WriteAllText(Path.Combine(basePatch,"shaders","lucinet_world.omwfx"),"# synthetic shader\n",Util.Utf8);
    string overlay=Path.Combine(temp,"world-reforged-overlay");string overlayFile=Path.Combine(overlay,"patch","textures","lucinet","fern.dds");Directory.CreateDirectory(Path.GetDirectoryName(overlayFile));File.WriteAllBytes(overlayFile,new byte[]{1,2,3});
    string pluginHash=Util.Hash(Path.Combine(basePatch,"LUCINET-World-Reforged.esp"));Util.Write(Path.Combine(overlay,"MANIFEST.json"),new WorldReforgedOverlay {Status="SYNTHETIC_TEST_ONLY",PluginSha256=pluginHash,Files=new List<WorldReforgedOverlayFile>{new WorldReforgedOverlayFile{Path="patch/textures/lucinet/fern.dds",Bytes=3,Sha256=Util.Hash(overlayFile)}}});
    Util.Write(Path.Combine(w.Root,"world-reforged-source.json"),new WorldReforgedLink {Schema="halveth.morrowind.world-reforged-link.v1",BasePatch=basePatch,CorrectiveOverlay=overlay,ExpectedPluginSha256=pluginHash});
    string runtime=w.PrepareProfile("world-reforged",s=>{});string worldCfg=Path.Combine(w.Root,"profiles","world-reforged","openmw.cfg");string worldText=File.ReadAllText(worldCfg,Util.Utf8);
    Check(Path.GetFullPath(runtime).StartsWith(Path.Combine(w.Root,"profiles","world-reforged"),StringComparison.OrdinalIgnoreCase),"World Reforged uses its own runtime");Check(File.Exists(Path.Combine(w.Root,"profiles","world-reforged","settings.cfg")),"World Reforged uses its own settings");Check(worldText.Contains("content=LUCINET-World-Reforged.esp"),"World Reforged plugin is bound into its own profile");Check(worldText.Contains("content=halveth.omwscripts"),"HALVETH gameplay extension is bound into World Reforged");Check(worldText.Contains("data="+Util.CfgPath(Path.Combine(w.Root,"mod"))),"HALVETH extension data path is bound into World Reforged");Check(!worldText.Contains("content=adamantiumarmor.esp"),"World Reforged excludes inherited optional add-ons");Check(worldText.IndexOf(basePatch.Replace('\\','/'),StringComparison.Ordinal)<worldText.IndexOf(Path.Combine(overlay,"patch").Replace('\\','/'),StringComparison.Ordinal),"World Reforged corrective overlay follows the base patch");w.ValidateLoadOrder(worldCfg);Check(true,"World Reforged plugin masters validate after base content");
    string worldCfgBeforeProbe=Util.Hash(worldCfg);var probe=w.PrepareSceneProbe("world-reforged",12,s=>{});string probeCfg=File.ReadAllText(probe.ConfigFile,Util.Utf8);string probeScript=File.ReadAllText(probe.ScriptFile,Util.Utf8);string globalProbeScript=File.ReadAllText(probe.GlobalScriptFile,Util.Utf8);
    Check(Util.Relative(w.Root,probe.ProbeRoot).StartsWith("probes/scene-",StringComparison.Ordinal),"Scene probe stays below the isolated candidate root");Check(probe.Arguments.Contains("--replace config --config"),"Scene probe replaces ambient config discovery");Check(probeCfg.Contains("user-data=")&&probeCfg.Contains("data-local="),"Scene probe binds its own user and local-data paths");Check(probeCfg.Contains("content=LUCINET-World-Reforged.esp")&&probeCfg.Contains("content=halveth_scene_probe.omwscripts"),"Scene probe keeps the World Reforged binding and adds only its own scripts");Check(probeScript.Contains("menu.newGame({ bypass = true })")&&probeScript.Contains("MENU_INIT")&&probeScript.Contains("NEW_GAME_REQUESTED"),"Menu script binds the new-game request markers");Check(globalProbeScript.Contains("onPlayerAdded")&&globalProbeScript.Contains("SCENE_RUNNING")&&!globalProbeScript.Contains("core.quit()"),"Global script binds the running-state marker without claiming its own clocked exit");Check(Util.Hash(worldCfg)==worldCfgBeforeProbe,"Scene probe does not rewrite the existing World Reforged profile config");
    Reject(()=>w.PrepareSceneProbe("classic",12,s=>{}),"Scene probe rejects an unbound profile");Reject(()=>w.PrepareSceneProbe("world-reforged",9,s=>{}),"Scene probe rejects an unsafe short watchdog");
    File.WriteAllBytes(overlayFile,new byte[]{9,9,9});Reject(()=>w.PrepareProfile("world-reforged",s=>{}),"Corrupt World Reforged overlay rejected before reuse");
    File.WriteAllBytes(overlayFile,new byte[]{1,2,3});File.Delete(Util.Inside(w.Root,"mod/scripts/halveth/worldlife.lua"));Reject(()=>w.PrepareProfile("world-reforged",s=>{}),"Missing HALVETH gameplay module rejected before reuse");
    string cfg=Path.Combine(temp,"load-order.cfg");File.WriteAllText(cfg,"content=Tribunal.esm\n",Util.Utf8);
    string atomic=Path.Combine(temp,"atomic.txt");Util.AtomicText(atomic,"before");Util.AtomicText(atomic,"after");Check(File.ReadAllText(atomic)=="after"&&Directory.GetFiles(temp,"atomic.txt.*.previous").Any(),"Config updates preserve previous file");
    Util.Write(output,new{status="PASS",checks=checks,passed=passed,scope="Synthetic local fixtures only. No game correctness or production completeness claim.",recordedUtc=DateTime.UtcNow.ToString("o")});return 0;
   }catch(Exception e){Util.Write(output,new{status="FAIL",checks=checks,error=e.ToString()});return 1;}
  }
 }
}
