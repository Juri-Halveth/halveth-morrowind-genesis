// HALVETH Morrowind Workshop · World Reforged Candidate 0.4.1. GPL-3.0-or-later; see LICENSE.txt.
// A data-preserving launcher. This code contains no Bethesda game content.
// This candidate keeps its own profiles and validates a bound local World Reforged overlay before use.
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using System.Web.Script.Serialization;

namespace Halveth.Morrowind {
  public static class Util {
    public static readonly UTF8Encoding Utf8 = new UTF8Encoding(false, true);
    public static string Stamp() { return DateTime.UtcNow.ToString("yyyyMMddTHHmmssfffZ"); }
    public static string Hash(string file) { using(var f=new FileStream(file,FileMode.Open,FileAccess.Read,FileShare.Read)) using(var h=SHA256.Create()) return Hex(h.ComputeHash(f)); }
    public static string Hex(byte[] b) { return BitConverter.ToString(b).Replace("-","").ToLowerInvariant(); }
    public static string Json(object value) { return new JavaScriptSerializer { MaxJsonLength=128*1024*1024 }.Serialize(value); }
    public static T Read<T>(string file) { return new JavaScriptSerializer { MaxJsonLength=128*1024*1024 }.Deserialize<T>(File.ReadAllText(file,Utf8)); }
    public static void Write(string file,object value) { Directory.CreateDirectory(Path.GetDirectoryName(file)); File.WriteAllText(file,Json(value),Utf8); }
    public static void AtomicText(string file,string text) {
      Directory.CreateDirectory(Path.GetDirectoryName(file)); string tmp=file+"."+Guid.NewGuid().ToString("N")+".tmp";
      File.WriteAllText(tmp,text,Utf8);
      if(File.Exists(file)) File.Replace(tmp,file,file+"."+Stamp()+".previous"); else File.Move(tmp,file);
    }
    public static string Inside(string root,string relative) {
      if(String.IsNullOrWhiteSpace(relative)||Path.IsPathRooted(relative)||relative.IndexOf(':')>=0||relative.IndexOf('\0')>=0) throw new InvalidDataException("Ungültiger relativer Pfad.");
      string[] parts=relative.Replace('\\','/').Split('/');
      if(parts.Any(p=>p==".."||p=="."||p.Length==0||p.EndsWith(".")||p.EndsWith(" "))) throw new InvalidDataException("Ungültiger Pfadbestandteil.");
      string basePath=Path.GetFullPath(root).TrimEnd('\\','/')+Path.DirectorySeparatorChar;
      string full=Path.GetFullPath(Path.Combine(basePath,relative));
      if(!full.StartsWith(basePath,StringComparison.OrdinalIgnoreCase)) throw new InvalidDataException("Pfad verlässt den Zielordner.");
      return full;
    }
    public static string CfgPath(string path) {
      if(path.IndexOfAny(new[]{'\r','\n','\0'})>=0) throw new InvalidDataException("Zeilenumbruch im Konfigurationspfad.");
      return "\""+path.Replace('\\','/').Replace("&","&&").Replace("\"","&\"")+"\"";
    }
    public static string Arg(string s) { // Windows CommandLineToArgvW quoting, without a shell.
      var b=new StringBuilder("\""); int slashes=0;
      foreach(char c in s) { if(c=='\\') {slashes++; continue;} if(c=='\"') b.Append('\\',slashes*2+1); else b.Append('\\',slashes); b.Append(c); slashes=0; }
      b.Append('\\',slashes*2); b.Append('"'); return b.ToString();
    }
    public static List<string> Files(string root) {
      var result=new List<string>(); var queue=new Queue<string>(); queue.Enqueue(Path.GetFullPath(root));
      while(queue.Count>0) {
        string dir=queue.Dequeue();
        if((File.GetAttributes(dir)&FileAttributes.ReparsePoint)!=0) throw new InvalidDataException("Verknüpfte Ordner werden nicht importiert: "+dir);
        foreach(string entry in Directory.EnumerateFileSystemEntries(dir)) {
          var attr=File.GetAttributes(entry);
          if((attr&FileAttributes.ReparsePoint)!=0) throw new InvalidDataException("Verknüpfte Datei wird nicht importiert: "+entry);
          if((attr&FileAttributes.Directory)!=0) queue.Enqueue(entry); else result.Add(entry);
          if(result.Count+queue.Count>250000) throw new InvalidDataException("Importgrenze von 250.000 Einträgen erreicht.");
        }
      }
      result.Sort(StringComparer.OrdinalIgnoreCase); return result;
    }
    public static void Start(string exe,string args,string cwd) {
      if(!File.Exists(exe)) throw new FileNotFoundException("Programm fehlt.",exe);
      Process.Start(new ProcessStartInfo(exe,args) { WorkingDirectory=cwd,UseShellExecute=false });
    }
    public static string Relative(string root,string file) {
      string basePath=Path.GetFullPath(root).TrimEnd('\\','/')+Path.DirectorySeparatorChar;
      string full=Path.GetFullPath(file);
      if(!full.StartsWith(basePath,StringComparison.OrdinalIgnoreCase)) throw new InvalidDataException("Datei liegt außerhalb des gebundenen Ordners.");
      return full.Substring(basePath.Length).Replace('\\','/');
    }
  }

  public class PluginInfo {
    public string FileName {get;set;}
    public Dictionary<string,int> Records {get;set;} = new Dictionary<string,int>();
    public List<string> Masters {get;set;} = new List<string>();
    public int Count {get;set;}
  }
  public class AssetInfo {
    public int Files {get;set;}
    public Dictionary<string,int> Categories {get;set;} = new Dictionary<string,int>(StringComparer.OrdinalIgnoreCase);
    public void Add(string name) {
      string n=name.Replace('\\','/').ToLowerInvariant(); string category=n.Contains("/")?n.Split('/')[0]:"root";
      if(!Categories.ContainsKey(category)) Categories[category]=0; Categories[category]++; Files++;
    }
  }
  public static class Inspect {
    static string Tag(BinaryReader r) { byte[] b=r.ReadBytes(4); if(b.Length!=4) throw new InvalidDataException("Abgeschnittener Datensatz."); string s=Encoding.ASCII.GetString(b); if(!Regex.IsMatch(s,"^[A-Z0-9_]{4}$")) throw new InvalidDataException("Ungültiger Datensatztyp."); return s; }
    public static PluginInfo Tes3(string file) {
      var info=new PluginInfo { FileName=Path.GetFileName(file) };
      using(var f=new FileStream(file,FileMode.Open,FileAccess.Read,FileShare.Read)) using(var r=new BinaryReader(f)) {
        if(f.Length<324||f.Length>2L*1024*1024*1024) throw new InvalidDataException("TES3-Dateigröße außerhalb des Prüfbereichs.");
        bool header=false;
        while(f.Position<f.Length) {
          if(f.Length-f.Position<16) throw new InvalidDataException("Abgeschnittener TES3-Recordheader.");
          string tag=Tag(r); uint size=r.ReadUInt32(); r.ReadUInt32(); r.ReadUInt32(); long end=f.Position+size;
          if(end>f.Length) throw new InvalidDataException("TES3-Record reicht über das Dateiende.");
          if(info.Count==0&&tag!="TES3") throw new InvalidDataException("TES3-Startsignatur fehlt.");
          if(info.Count>0&&tag=="TES3") throw new InvalidDataException("Mehrfacher TES3-Header.");
          if(tag=="TES3") {
            while(f.Position<end) {
              if(end-f.Position<8) throw new InvalidDataException("Abgeschnittener TES3-Subheader.");
              string sub=Tag(r); uint n=r.ReadUInt32(); long subEnd=f.Position+n;
              if(subEnd>end) throw new InvalidDataException("TES3-Subrecord überschreitet den Header.");
              if(sub=="HEDR") { if(n!=300||header) throw new InvalidDataException("Ungültiger HEDR."); header=true; }
              if(sub=="MAST") {
                if(n<2||n>512) throw new InvalidDataException("Ungültiger Mastername.");
                byte[] raw=r.ReadBytes((int)n); if(raw[raw.Length-1]!=0) throw new InvalidDataException("Mastername ohne Abschluss.");
                string name=Encoding.GetEncoding(1252).GetString(raw,0,raw.Length-1);
                if(name!=Path.GetFileName(name)||name.IndexOfAny(new[]{'\r','\n','\0',':','/','\\'})>=0) throw new InvalidDataException("Ungültiger Masterpfad.");
                info.Masters.Add(name);
              }
              f.Position=subEnd;
            }
          }
          if(!info.Records.ContainsKey(tag)) info.Records[tag]=0; info.Records[tag]++; info.Count++;
          if(info.Count>2000000) throw new InvalidDataException("Zu viele TES3-Datensätze.");
          f.Position=end;
        }
        if(!header) throw new InvalidDataException("TES3-HEDR fehlt.");
      }
      return info;
    }
    // TES3 BSA layout checked against OpenMW 0.51.0 components/bsa/bsafile.cpp.
    // This inspects indexes only; it does not decode or execute asset payloads.
    public static AssetInfo Bsa(string file) {
      var info=new AssetInfo();
      using(var f=new FileStream(file,FileMode.Open,FileAccess.Read,FileShare.Read)) using(var r=new BinaryReader(f)) {
        if(f.Length<12||r.ReadUInt32()!=0x100) throw new InvalidDataException("TES3-BSA-Signatur fehlt.");
        long dir=r.ReadUInt32(); int count=checked((int)r.ReadUInt32()); long data=12+dir+8L*count;
        if(count<1||count>1000000||dir<12L*count||dir>128*1024*1024||data>f.Length) throw new InvalidDataException("Ungültiges BSA-Verzeichnis.");
        uint[] sizes=new uint[count],offsets=new uint[count],names=new uint[count];
        for(int i=0;i<count;i++){ sizes[i]=r.ReadUInt32(); offsets[i]=r.ReadUInt32(); if(data+offsets[i]+sizes[i]>f.Length) throw new InvalidDataException("BSA-Datei außerhalb des Archivs."); }
        for(int i=0;i<count;i++) names[i]=r.ReadUInt32();
        byte[] buf=r.ReadBytes((int)(dir-12L*count)); var unique=new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        for(int i=0;i<count;i++) {
          if(names[i]>=buf.Length) throw new InvalidDataException("BSA-Namensoffset außerhalb des Verzeichnisses.");
          int start=(int)names[i],stop=start; while(stop<buf.Length&&buf[stop]!=0&&stop-start<4096) stop++;
          if(stop>=buf.Length||buf[stop]!=0||stop==start) throw new InvalidDataException("Ungültiger BSA-Dateiname.");
          string name=Encoding.GetEncoding(1252).GetString(buf,start,stop-start).Replace('\\','/');
          Util.Inside(Path.GetTempPath(),name);
          if(!unique.Add(name)) throw new InvalidDataException("Mehrdeutiger BSA-Dateiname.");
          info.Add(name);
        }
      }
      return info;
    }
  }

  public class FileReceipt { public string Path {get;set;} public long Bytes {get;set;} public string Sha256 {get;set;} }
  public class ImportReceipt {
    public string Id {get;set;}
    public string RecordedUtc {get;set;}
    public string Scope {get;set;} = "STRUCTURE_AND_COPY_INTEGRITY; not publisher provenance or gameplay completeness";
    public List<FileReceipt> Files {get;set;} = new List<FileReceipt>();
    public List<PluginInfo> Plugins {get;set;} = new List<PluginInfo>();
    public Dictionary<string,AssetInfo> Archives {get;set;} = new Dictionary<string,AssetInfo>();
    public AssetInfo LooseAssets {get;set;} = new AssetInfo();
    public List<string> Warnings {get;set;} = new List<string>();
  }
  public class State { public string ActiveImport {get;set;} public string Profile {get;set;} = "world-reforged"; }
  public class WorldReforgedLink {
    public string Schema {get;set;}
    public string BasePatch {get;set;}
    public string CorrectiveOverlay {get;set;}
    public string ExpectedPluginSha256 {get;set;}
  }
  public class WorldReforgedOverlayFile {
    public string Path {get;set;}
    public long Bytes {get;set;}
    public string Sha256 {get;set;}
  }
  public class WorldReforgedOverlay {
    public string Status {get;set;}
    public string PluginSha256 {get;set;}
    public List<WorldReforgedOverlayFile> Files {get;set;}
  }
  public class WorldReforgedBinding {
    public string BasePatch {get;set;}
    public string CorrectiveOverlay {get;set;}
    public string BasePluginSha256 {get;set;}
    public string OverlayManifestSha256 {get;set;}
  }
  public class HalvethExtensionManifest {
    public string Schema {get;set;}
    public List<FileReceipt> Files {get;set;}
    public string Scope {get;set;}
  }
  public class HalvethExtensionBinding {
    public string DataDirectory {get;set;}
    public string ManifestSha256 {get;set;}
  }
  public class SceneProbePlan {
    public string ProbeId {get;set;}
    public string ProbeRoot {get;set;}
    public string ConfigDirectory {get;set;}
    public string Runtime {get;set;}
    public string EngineExecutable {get;set;}
    public string Arguments {get;set;}
    public string ConfigFile {get;set;}
    public string ScriptFile {get;set;}
    public string GlobalScriptFile {get;set;}
    public string ProfileConfigSha256 {get;set;}
    public int MaximumSeconds {get;set;}
  }
  public class SceneProbeLogReceipt {
    public string Path {get;set;}
    public long Bytes {get;set;}
    public string Sha256 {get;set;}
  }
  public class SceneProbeReceipt {
    public string Schema {get;set;} = "halveth.morrowind.scene-probe.v2";
    public string ProbeId {get;set;}
    public string Profile {get;set;}
    public string Status {get;set;}
    public string RecordedUtc {get;set;}
    public string StartedUtc {get;set;}
    public string FinishedUtc {get;set;}
    public int MaximumSeconds {get;set;}
    public bool ProcessStarted {get;set;}
    public bool ProcessExited {get;set;}
    public int? ProcessExitCode {get;set;}
    public bool WatchdogTriggered {get;set;}
    public int RequestedSceneDwellSeconds {get;set;}
    public string SceneRunningObservedUtc {get;set;}
    public string ControllerStopRequestedUtc {get;set;}
    public bool ControllerStopAfterSceneMarker {get;set;}
    public string StopMethod {get;set;}
    public string ErrorKind {get;set;}
    public string EngineSha256 {get;set;}
    public string ProfileConfigSha256 {get;set;}
    public List<FileReceipt> Inputs {get;set;} = new List<FileReceipt>();
    public List<SceneProbeLogReceipt> Logs {get;set;} = new List<SceneProbeLogReceipt>();
    public List<string> UnreadableLogs {get;set;} = new List<string>();
    public Dictionary<string,bool> Markers {get;set;} = new Dictionary<string,bool>();
    public string Scope {get;set;} = "Owned local candidate only; isolated probe configuration, user data, data-local files, and logs live beneath probes/<id>.";
    public string ClaimCeiling {get;set;} = "At most a bounded menu-to-new-game-to-player-added transition witness and recorded local controller stop. It does not prove visual acceptance, FPS, collision, save correctness, or gameplay completeness.";
  }
  public class Workshop {
    public readonly string Root;
    public State State;
    public static readonly string[] ProfileIds={"classic","max","ultra","world-reforged"};
    public static readonly string[] ProfileNames={"Klassik · OpenMW","Weitsicht · ausgewogen","Ultra · Experiment","Welt Reforged · Genesis"};
    public static readonly string[] RequiredHalvethFiles={
      "mod/halveth.omwscripts","mod/Fonts/MysticCards.omwfont","mod/shaders/halveth_atmosphere.omwfx",
      "mod/Textures/halveth/love-astrolabe-0.7.png","mod/Textures/halveth/scarlet-love-banner.png",
      "mod/bridge/inbox.json","mod/bridge/companion-status.json",
      "mod/scripts/halveth/actor_life.lua","mod/scripts/halveth/actor_life_global.lua","mod/scripts/halveth/common.lua",
      "mod/scripts/halveth/content.lua","mod/scripts/halveth/content_catalog.lua","mod/scripts/halveth/fieldcraft.lua",
      "mod/scripts/halveth/global.lua","mod/scripts/halveth/inspect.lua","mod/scripts/halveth/knowledge.lua",
      "mod/scripts/halveth/paths.lua","mod/scripts/halveth/perspective.lua","mod/scripts/halveth/player.lua",
      "mod/scripts/halveth/universe.lua","mod/scripts/halveth/visuals.lua","mod/scripts/halveth/worldlife.lua"
    };
    public Workshop(string root) {
      Root=Path.GetFullPath(root);
      foreach(string d in new[]{"library","profiles","history","evidence","mods"}) Directory.CreateDirectory(Path.Combine(Root,d));
      string stateFile=Path.Combine(Root,"state.json"); State=File.Exists(stateFile)?Util.Read<State>(stateFile):new State();
      if(!ProfileIds.Contains(State.Profile)) throw new InvalidDataException("Unbekanntes Profil in state.json.");
    }
    public void Save() { Util.AtomicText(Path.Combine(Root,"state.json"),Util.Json(State)); }
    static string LocalDirectory(string path,string label) {
      if(String.IsNullOrWhiteSpace(path)) throw new InvalidDataException(label+" fehlt.");
      string full=Path.GetFullPath(path).TrimEnd('\\','/');
      if(full.StartsWith("\\\\",StringComparison.Ordinal)) throw new InvalidDataException(label+" darf kein Netzwerkpfad sein.");
      var info=new DirectoryInfo(full); if(!info.Exists) throw new InvalidDataException(label+" fehlt: "+full);
      for(var current=info;current!=null;current=current.Parent) if((current.Attributes&FileAttributes.ReparsePoint)!=0) throw new InvalidDataException(label+" enthält eine Ordnerverknüpfung.");
      return full;
    }
    static void PlainFile(string file,string label) {
      if(!File.Exists(file)) throw new InvalidDataException(label+" fehlt: "+file);
      if((File.GetAttributes(file)&FileAttributes.ReparsePoint)!=0) throw new InvalidDataException(label+" darf keine Dateiverknüpfung sein.");
    }
    public WorldReforgedBinding ValidateWorldReforged() {
      string linkFile=Path.Combine(Root,"world-reforged-source.json");
      if(!File.Exists(linkFile)) throw new InvalidDataException("Die lokale World-Reforged-Quellenbindung fehlt.");
      var link=Util.Read<WorldReforgedLink>(linkFile); if(link==null) throw new InvalidDataException("Die lokale World-Reforged-Quellenbindung ist leer.");
      string basePatch=LocalDirectory(link.BasePatch,"World-Reforged-Basispatch");
      string overlayRoot=LocalDirectory(link.CorrectiveOverlay,"World-Reforged-Korrekturoverlay");
      string expected=(link.ExpectedPluginSha256??"").ToLowerInvariant();
      if(!Regex.IsMatch(expected,"^[0-9a-f]{64}$")) throw new InvalidDataException("Die erwartete World-Reforged-Plugin-Prüfsumme ist ungültig.");
      string plugin=Path.Combine(basePatch,"LUCINET-World-Reforged.esp"); PlainFile(plugin,"Der gebundene World-Reforged-Basispatch");
      if(!String.Equals(Util.Hash(plugin),expected,StringComparison.OrdinalIgnoreCase)) throw new InvalidDataException("Der gebundene World-Reforged-Basispatch stimmt nicht mit seiner Plugin-Prüfsumme überein.");
      PlainFile(Path.Combine(basePatch,"shaders","lucinet_world.omwfx"),"Der Weltshader im gebundenen Basispatch");
      string manifestFile=Path.Combine(overlayRoot,"MANIFEST.json"); PlainFile(manifestFile,"Das World-Reforged-Korrekturoverlay-Manifest");
      var manifest=Util.Read<WorldReforgedOverlay>(manifestFile);
      if(manifest==null||!String.Equals(manifest.PluginSha256,expected,StringComparison.OrdinalIgnoreCase)||manifest.Files==null||manifest.Files.Count==0) throw new InvalidDataException("Das World-Reforged-Korrekturoverlay passt nicht zum gebundenen Basispatch.");
      var seen=new HashSet<string>(StringComparer.OrdinalIgnoreCase);
      foreach(var item in manifest.Files) {
        if(item==null||String.IsNullOrWhiteSpace(item.Path)||item.Bytes<0||!Regex.IsMatch(item.Path,"^patch/(Meshes|textures)/lucinet/[A-Za-z0-9_.-]+$")||!Regex.IsMatch(item.Sha256??"","^[0-9a-fA-F]{64}$")||!seen.Add(item.Path)) throw new InvalidDataException("Das World-Reforged-Korrekturoverlay enthält einen ungültigen Dateieintrag.");
        string file=Util.Inside(overlayRoot,item.Path); PlainFile(file,"Die gebundene World-Reforged-Korrekturdatei");
        if(new FileInfo(file).Length!=item.Bytes||!String.Equals(Util.Hash(file),item.Sha256,StringComparison.OrdinalIgnoreCase)) throw new InvalidDataException("Die gebundene World-Reforged-Korrekturdatei stimmt nicht mit dem Manifest überein: "+item.Path);
      }
      return new WorldReforgedBinding {BasePatch=basePatch,CorrectiveOverlay=overlayRoot,BasePluginSha256=expected,OverlayManifestSha256=Util.Hash(manifestFile)};
    }
    public HalvethExtensionBinding ValidateHalvethExtension() {
      string manifestFile=Path.Combine(Root,"halveth-extension.json"); PlainFile(manifestFile,"Das HALVETH-Erweiterungsmanifest");
      var manifest=Util.Read<HalvethExtensionManifest>(manifestFile);
      if(manifest==null||manifest.Schema!="halveth.morrowind.own-extension.v1"||manifest.Files==null||manifest.Files.Count!=RequiredHalvethFiles.Length) throw new InvalidDataException("Das HALVETH-Erweiterungsmanifest ist unvollständig oder hat ein unbekanntes Schema.");
      var seen=new HashSet<string>(StringComparer.Ordinal);
      foreach(var item in manifest.Files) {
        if(item==null||String.IsNullOrWhiteSpace(item.Path)||item.Bytes<0||!Regex.IsMatch(item.Sha256??"","^[0-9a-fA-F]{64}$")||!RequiredHalvethFiles.Contains(item.Path,StringComparer.Ordinal)||!seen.Add(item.Path)) throw new InvalidDataException("Das HALVETH-Erweiterungsmanifest enthält einen ungültigen Dateieintrag.");
        string file=Util.Inside(Root,item.Path); PlainFile(file,"Eine HALVETH-Erweiterungsdatei");
        if(new FileInfo(file).Length!=item.Bytes||!String.Equals(Util.Hash(file),item.Sha256,StringComparison.OrdinalIgnoreCase)) throw new InvalidDataException("Die HALVETH-Erweiterungsdatei stimmt nicht mit ihrem Manifest überein: "+item.Path);
      }
      if(!RequiredHalvethFiles.All(path=>seen.Contains(path))) throw new InvalidDataException("Das HALVETH-Erweiterungsmanifest deckt nicht alle erforderlichen Spielmodule ab.");
      return new HalvethExtensionBinding {DataDirectory=Path.Combine(Root,"mod"),ManifestSha256=Util.Hash(manifestFile)};
    }
    public string DataRoot() {
      if(String.IsNullOrEmpty(State.ActiveImport)) return null;
      if(!Regex.IsMatch(State.ActiveImport,"^[a-zA-Z0-9-]+$")) throw new InvalidDataException("Ungültige Import-ID.");
      string root=Util.Inside(Root,"library/"+State.ActiveImport+"/Data Files");
      if(!File.Exists(Path.Combine(root,"Morrowind.esm"))) throw new InvalidDataException("Der aktive Datenimport fehlt.");
      return root;
    }
    public ImportReceipt Receipt() { string d=DataRoot(); return d==null?null:Util.Read<ImportReceipt>(Path.Combine(Directory.GetParent(d).FullName,"receipt.json")); }
    List<string> ContentLines(string id,string data,string dataConfigPath,WorldReforgedBinding worldReforged,HalvethExtensionBinding extension,string extraData,string extraContent) {
      var lines=new List<string>();
      if(data!=null) {
        lines.Add("data="+Util.CfgPath(dataConfigPath));
        foreach(string name in new[]{"Morrowind","Tribunal","Bloodmoon"}) if(File.Exists(Path.Combine(data,name+".esm"))) {lines.Add("fallback-archive="+name+".bsa"); lines.Add("content="+name+".esm");}
        if(id!="classic"&&id!="world-reforged") {
          foreach(string addon in new[]{"adamantiumarmor.esp","AreaEffectArrows.esp","bcsounds.esp","EBQ_Artifact.esp","entertainers.esp","LeFemmArmor.esp","master_index.esp","Siege at Firemoth.esp"}) if(File.Exists(Path.Combine(data,addon))) lines.Add("content="+addon);
          var bound=Receipt();
          if(bound!=null&&bound.Files.Any(f=>f.Path.Equals("Morrowind.esm",StringComparison.OrdinalIgnoreCase)&&f.Sha256=="5c3c8c2cbd20e25901b59b3ece33d36b7ef0e3d60ad8d11828bcc61a5ead1647")) {
            lines.Add("data=../../mods/compatibility");lines.Add("content=HALVETH-Dialogue-Compatibility.esp");
          }
        }
      }
      if(worldReforged!=null) {
        lines.Add("data="+Util.CfgPath(worldReforged.BasePatch));
        lines.Add("data="+Util.CfgPath(Path.Combine(worldReforged.CorrectiveOverlay,"patch")));
        lines.Add("data="+Util.CfgPath(extension.DataDirectory));
        lines.Add("content=LUCINET-World-Reforged.esp");
        lines.Add("content=halveth.omwscripts");
      }
      if(!String.IsNullOrEmpty(extraData)) lines.Add("data="+Util.CfgPath(extraData));
      if(!String.IsNullOrEmpty(extraContent)) lines.Add("content="+extraContent);
      return lines;
    }
    public ImportReceipt Import(string esm,Action<string> progress) {
      string source=Path.GetDirectoryName(Path.GetFullPath(esm));
      if(!String.Equals(Path.GetFileName(esm),"Morrowind.esm",StringComparison.OrdinalIgnoreCase)) throw new InvalidDataException("Bitte Morrowind.esm aus dem Ordner Data Files auswählen.");
      if(source.StartsWith(Root.TrimEnd('\\')+"\\",StringComparison.OrdinalIgnoreCase)) throw new InvalidDataException("Wähle die Originalquelle außerhalb dieser Werkstatt.");
      progress("Prüfe Morrowind.esm und Morrowind.bsa …");
      var basePlugin=Inspect.Tes3(esm);
      foreach(string tag in new[]{"CELL","NPC_","LAND","GMST"}) if(!basePlugin.Records.ContainsKey(tag)) throw new InvalidDataException("Basisspiel enthält keine "+tag+"-Records.");
      Inspect.Bsa(Path.Combine(source,"Morrowind.bsa"));
      var files=Util.Files(source); long bytes=files.Sum(p=>new FileInfo(p).Length);
      if(bytes>128L*1024*1024*1024) throw new InvalidDataException("Import ist größer als 128 GiB.");
      if(new DriveInfo(Path.GetPathRoot(Root)).AvailableFreeSpace<bytes+512L*1024*1024) throw new IOException("Zu wenig freier Speicher für die erhaltene Datenkopie.");
      var receipt=new ImportReceipt { Id="import-"+Util.Stamp()+"-"+Guid.NewGuid().ToString("N").Substring(0,8),RecordedUtc=DateTime.UtcNow.ToString("o") };
      string folder=Path.Combine(Root,"library",receipt.Id); string target=Path.Combine(folder,"Data Files"); Directory.CreateDirectory(target);
      Util.Write(Path.Combine(folder,"IMPORTING.json"),new {status="IMPORTING",recordedUtc=receipt.RecordedUtc});
      int copied=0;
      foreach(string file in files) {
        string relative=file.Substring(source.TrimEnd('\\','/').Length+1); string dest=Util.Inside(target,relative); Directory.CreateDirectory(Path.GetDirectoryName(dest));
        if(copied%50==0) progress("Kopiere und hashe "+copied+" / "+files.Count+" Dateien …");
        string hash;
        using(var input=new FileStream(file,FileMode.Open,FileAccess.Read,FileShare.Read))
        using(var output=new FileStream(dest,FileMode.CreateNew,FileAccess.Write,FileShare.None))
        using(var sha=SHA256.Create()) {
          var buffer=new byte[1024*1024]; int n;
          while((n=input.Read(buffer,0,buffer.Length))>0) { output.Write(buffer,0,n); sha.TransformBlock(buffer,0,n,null,0); }
          sha.TransformFinalBlock(new byte[0],0,0); hash=Util.Hex(sha.Hash);
        }
        if(Util.Hash(dest)!=hash) throw new IOException("Kopierprüfung fehlgeschlagen: "+relative);
        receipt.Files.Add(new FileReceipt {Path=relative.Replace('\\','/'),Bytes=new FileInfo(dest).Length,Sha256=hash}); receipt.LooseAssets.Add(relative); copied++;
      }
      foreach(string file in Directory.GetFiles(target)) {
        string ext=Path.GetExtension(file).ToLowerInvariant();
        if(new[]{".esm",".esp",".omwgame",".omwaddon"}.Contains(ext)) receipt.Plugins.Add(Inspect.Tes3(file));
        if(ext==".bsa") receipt.Archives.Add(Path.GetFileName(file),Inspect.Bsa(file));
      }
      if(!receipt.LooseAssets.Categories.ContainsKey("music")) receipt.Warnings.Add("Kein Music-Ordner in der Quelle gefunden; Originalmusik ist damit nicht als vollständig vorhanden belegt.");
      if(!receipt.LooseAssets.Categories.ContainsKey("sound")&&!receipt.Archives.Values.Any(a=>a.Categories.ContainsKey("sound"))) receipt.Warnings.Add("Keine Sound-Dateien im geprüften Inventar gefunden.");
      foreach(string expansion in new[]{"Tribunal","Bloodmoon"}) if(File.Exists(Path.Combine(target,expansion+".esm"))!=File.Exists(Path.Combine(target,expansion+".bsa"))) throw new InvalidDataException("Unvollständige Erweiterung: "+expansion+". Import bleibt inaktiv.");
      receipt.Warnings.Add("ESM/BSA-Struktur und Kopiergleichheit geprüft. Vollständigkeit aller Spielreferenzen und Spielbarkeit benötigen den Lauf mit diesen Daten.");
      string ini=Path.Combine(Directory.GetParent(source).FullName,"Morrowind.ini");
      if(File.Exists(ini)) File.Copy(ini,Path.Combine(folder,"Morrowind.ini.original"));
      Util.Write(Path.Combine(folder,"receipt.json"),receipt);
      Util.Write(Path.Combine(folder,"COMPLETED.json"),new {status="COPY_VERIFIED_AND_STRUCTURALLY_INSPECTED",recordedUtc=DateTime.UtcNow.ToString("o")});
      State.ActiveImport=receipt.Id; Save(); progress("Datenkopie übernommen. "+receipt.Files.Count+" Dateien erhalten."); return receipt;
    }
    public string PrepareProfile(string id,Action<string> progress) {
      if(!ProfileIds.Contains(id)) throw new InvalidDataException("Unbekanntes Profil.");
      WorldReforgedBinding worldReforged=id=="world-reforged"?ValidateWorldReforged():null;
      HalvethExtensionBinding extension=id=="world-reforged"?ValidateHalvethExtension():null;
      string profile=Path.Combine(Root,"profiles",id),runtime=Path.Combine(profile,"runtime");
      string engine=Path.Combine(Root,"engine");
      PlainFile(Path.Combine(engine,"openmw.cfg"),"Die lokale OpenMW-Laufzeitkonfiguration");
      PlainFile(Path.Combine(engine,"openmw.exe"),"Die lokale OpenMW-Laufzeit");
      Directory.CreateDirectory(profile); Directory.CreateDirectory(Path.Combine(profile,"data")); Directory.CreateDirectory(Path.Combine(profile,"user"));
      if(!File.Exists(Path.Combine(runtime,".runtime-ready"))) {
        progress("Richte getrennte Laufzeit für dieses Profil ein …");
        foreach(string file in Util.Files(engine)) {
          string rel=file.Substring(engine.Length+1),dest=Util.Inside(runtime,rel); Directory.CreateDirectory(Path.GetDirectoryName(dest));
          if(File.Exists(dest)) { if(Util.Hash(dest)!=Util.Hash(file)) throw new InvalidDataException("Unvollständige Laufzeit enthält eine abweichende Datei: "+rel); }
          else File.Copy(file,dest);
        }
        File.WriteAllText(Path.Combine(runtime,".runtime-ready"),"OpenMW 0.51.0\n",Util.Utf8);
      }
      PlainFile(Path.Combine(runtime,"openmw.cfg"),"Die getrennte OpenMW-Laufzeitkonfiguration");
      PlainFile(Path.Combine(runtime,"openmw.exe"),"Die getrennte OpenMW-Laufzeit");
      string baseCfg=File.ReadAllText(Path.Combine(engine,"openmw.cfg"),Util.Utf8);
      var keep=baseCfg.Split(new[]{'\r','\n'},StringSplitOptions.RemoveEmptyEntries).Where(l=>!Regex.IsMatch(l.Trim(),"^(data-local|user-data|config|resources|data)=")).ToArray();
      string runtimeCfg="# Isolated portable runtime. Default global user configuration is not loaded.\n"+
        "config=..\nresources=./resources\ndata=./resources/vfs-mw\nuser-data=../user\ndata-local=../data\n"+String.Join("\n",keep)+"\n";
      Util.AtomicText(Path.Combine(runtime,"openmw.cfg"),runtimeCfg);
      string cfg=Path.Combine(profile,"openmw.cfg"),data=DataRoot();
      string bindingFile=Path.Combine(profile,"import-binding.txt");
      string binding=(State.ActiveImport??"NONE")+(worldReforged==null?"":"|world-reforged|"+worldReforged.BasePluginSha256+"|"+worldReforged.OverlayManifestSha256+"|"+extension.ManifestSha256);
      if(!File.Exists(cfg)||!File.Exists(bindingFile)||File.ReadAllText(bindingFile)!=binding) {
        string userPath="user/"+(State.ActiveImport??"NONE"); Directory.CreateDirectory(Path.Combine(profile,userPath));
        var lines=new List<string>{"# Generated baseline; native OpenMW launcher may extend this profile.","user-data="+userPath,"data-local=data","encoding=win1252"};
        lines.AddRange(ContentLines(id,data,"../../library/"+State.ActiveImport+"/Data Files",worldReforged,extension,null,null));
        Util.AtomicText(cfg,String.Join("\n",lines)+"\n");
        Util.AtomicText(bindingFile,binding);
      }
      string settings=Path.Combine(profile,"settings.cfg");
      if(!File.Exists(settings)) File.Copy(Path.Combine(Root,"presets",id+".cfg"),settings);
      State.Profile=id; Save(); return runtime;
    }
    static readonly string[] SceneProbeMarkers={"MENU_INIT","NEW_GAME_REQUESTED","SCENE_RUNNING"};
    const int SceneProbeDwellSeconds=8;
    static string SceneProbeScript() {
      return String.Join("\n",new[]{
        "local menu = require('openmw.menu')",
        "",
        "local function mark(value)",
        "  print('[HALVETH_SCENE_PROBE] ' .. value)",
        "end",
        "",
        "return {",
        "  engineHandlers = {",
        "    onInit = function()",
        "      mark('MENU_INIT')",
        "      menu.newGame({ bypass = true })",
        "      mark('NEW_GAME_REQUESTED')",
        "    end",
        "  }",
        "}",
        ""
      });
    }
    static string SceneProbeGlobalScript() {
      return String.Join("\n",new[]{
        "local running = false",
        "",
        "local function mark(value)",
        "  print('[HALVETH_SCENE_PROBE] ' .. value)",
        "end",
        "",
        "return {",
        "  engineHandlers = {",
        "    onPlayerAdded = function()",
        "      if running then return end",
        "      running = true",
        "      mark('SCENE_RUNNING')",
        "    end",
        "  }",
        "}",
        ""
      });
    }
    public SceneProbePlan PrepareSceneProbe(string id,int maximumSeconds,Action<string> progress) {
      if(!String.Equals(id,"world-reforged",StringComparison.Ordinal)) throw new InvalidDataException("Die Szenenprobe ist nur für das gebundene World-Reforged-Profil vorgesehen.");
      if(maximumSeconds<10||maximumSeconds>75) throw new InvalidDataException("Die Szenenprobe muss zwischen 10 und 75 Sekunden begrenzt sein.");
      if(DataRoot()==null) throw new InvalidDataException("Für die Szenenprobe zuerst Morrowind.esm aus einer vollständigen Datenquelle importieren.");
      string runtime=PrepareProfile(id,progress),profileCfg=Path.Combine(Root,"profiles",id,"openmw.cfg");
      ValidateLoadOrder(profileCfg);
      string probeId="scene-"+Util.Stamp()+"-"+Guid.NewGuid().ToString("N").Substring(0,8);
      string probeRoot=Util.Inside(Root,"probes/"+probeId),config=Path.Combine(probeRoot,"config"),probeData=Path.Combine(probeRoot,"data"),user=Path.Combine(probeRoot,"user"),logs=Path.Combine(probeRoot,"logs");
      Directory.CreateDirectory(config);Directory.CreateDirectory(probeData);Directory.CreateDirectory(user);Directory.CreateDirectory(logs);
      string scriptDir=Path.Combine(probeData,"scripts","halveth_scene_probe"),scriptFile=Path.Combine(scriptDir,"menu.lua"),globalScriptFile=Path.Combine(scriptDir,"global.lua"),manifest=Path.Combine(probeData,"halveth_scene_probe.omwscripts");
      Directory.CreateDirectory(scriptDir);
      Util.AtomicText(scriptFile,SceneProbeScript());
      Util.AtomicText(globalScriptFile,SceneProbeGlobalScript());
      Util.AtomicText(manifest,"MENU: scripts/halveth_scene_probe/menu.lua\nGLOBAL: scripts/halveth_scene_probe/global.lua\n");
      var worldReforged=ValidateWorldReforged(); var extension=ValidateHalvethExtension();
      var lines=new List<string>{
        "# Generated isolated local scene probe. It is selected with --replace config.",
        "resources="+Util.CfgPath(Path.Combine(runtime,"resources")),
        "data="+Util.CfgPath(Path.Combine(runtime,"resources","vfs-mw")),
        "user-data="+Util.CfgPath(user),
        "data-local="+Util.CfgPath(probeData),
        "encoding=win1252"
      };
      string importedData=DataRoot();
      lines.AddRange(ContentLines(id,importedData,importedData,worldReforged,extension,probeData,"halveth_scene_probe.omwscripts"));
      string configFile=Path.Combine(config,"openmw.cfg");Util.AtomicText(configFile,String.Join("\n",lines)+"\n");
      return new SceneProbePlan {
        ProbeId=probeId,ProbeRoot=probeRoot,ConfigDirectory=config,Runtime=runtime,EngineExecutable=Path.Combine(runtime,"openmw.exe"),
        Arguments="--replace config --config "+Util.Arg(config),ConfigFile=configFile,ScriptFile=scriptFile,GlobalScriptFile=globalScriptFile,ProfileConfigSha256=Util.Hash(profileCfg),MaximumSeconds=maximumSeconds
      };
    }
    static void CaptureLine(List<string> lines,object gate,ref int capturedBytes,ref bool truncated,ManualResetEvent sceneRunning,string channel,string line) {
      if(line==null) return;
      if(line.IndexOf("[HALVETH_SCENE_PROBE] SCENE_RUNNING",StringComparison.Ordinal)>=0) sceneRunning.Set();
      lock(gate) {
        if(truncated) return;
        string item="["+channel+"] "+line;
        int bytes=Encoding.UTF8.GetByteCount(item)+2;
        if(capturedBytes+bytes>1024*1024) {truncated=true;lines.Add("[WORKSHOP] output capture limit reached");return;}
        lines.Add(item);capturedBytes+=bytes;
      }
    }
    static List<SceneProbeLogReceipt> ReadProbeLogs(string probeRoot,Dictionary<string,bool> markers,List<string> unreadable) {
      var receipts=new List<SceneProbeLogReceipt>();
      foreach(string file in Util.Files(probeRoot)) {
        string ext=Path.GetExtension(file);
        if(!String.Equals(ext,".log",StringComparison.OrdinalIgnoreCase)&&!String.Equals(ext,".txt",StringComparison.OrdinalIgnoreCase)) continue;
        string relative=Util.Relative(probeRoot,file);
        receipts.Add(new SceneProbeLogReceipt {Path=relative,Bytes=new FileInfo(file).Length,Sha256=Util.Hash(file)});
        try {
          string text=File.ReadAllText(file,Encoding.UTF8);
          foreach(string marker in SceneProbeMarkers) if(text.IndexOf(marker,StringComparison.Ordinal)>=0) markers[marker]=true;
        } catch(IOException) { unreadable.Add(relative); }
          catch(UnauthorizedAccessException) { unreadable.Add(relative); }
          catch(DecoderFallbackException) { unreadable.Add(relative); }
      }
      return receipts;
    }
    static bool AllMarkers(Dictionary<string,bool> markers) { return SceneProbeMarkers.All(marker=>markers.ContainsKey(marker)&&markers[marker]); }
    static void StopProbeProcess(Process process,SceneProbeReceipt receipt,string requestedMethod,string forcedMethod) {
      receipt.StopMethod=requestedMethod;
      try { process.CloseMainWindow(); } catch(InvalidOperationException) { }
      if(!process.WaitForExit(2500)) {
        receipt.StopMethod=forcedMethod;
        try { process.Kill(); } catch(InvalidOperationException) { }
        process.WaitForExit(10000);
      }
    }
    void WriteSceneProbeReceipt(SceneProbePlan plan,SceneProbeReceipt receipt) {
      Util.Write(Path.Combine(plan.ProbeRoot,"scene-probe-receipt.json"),receipt);
      Util.Write(Path.Combine(Root,"evidence","scene-probe-"+plan.ProbeId+".json"),receipt);
    }
    public SceneProbeReceipt RunSceneProbe(string id,int maximumSeconds,Action<string> progress) {
      var plan=PrepareSceneProbe(id,maximumSeconds,progress);
      var receipt=new SceneProbeReceipt {ProbeId=plan.ProbeId,Profile=id,RecordedUtc=DateTime.UtcNow.ToString("o"),MaximumSeconds=maximumSeconds,RequestedSceneDwellSeconds=SceneProbeDwellSeconds,EngineSha256=Util.Hash(plan.EngineExecutable),ProfileConfigSha256=plan.ProfileConfigSha256};
      receipt.Inputs.Add(new FileReceipt {Path="config/openmw.cfg",Bytes=new FileInfo(plan.ConfigFile).Length,Sha256=Util.Hash(plan.ConfigFile)});
      receipt.Inputs.Add(new FileReceipt {Path="data/halveth_scene_probe.omwscripts",Bytes=new FileInfo(Path.Combine(plan.ProbeRoot,"data","halveth_scene_probe.omwscripts")).Length,Sha256=Util.Hash(Path.Combine(plan.ProbeRoot,"data","halveth_scene_probe.omwscripts"))});
      receipt.Inputs.Add(new FileReceipt {Path="data/scripts/halveth_scene_probe/menu.lua",Bytes=new FileInfo(plan.ScriptFile).Length,Sha256=Util.Hash(plan.ScriptFile)});
      receipt.Inputs.Add(new FileReceipt {Path="data/scripts/halveth_scene_probe/global.lua",Bytes=new FileInfo(plan.GlobalScriptFile).Length,Sha256=Util.Hash(plan.GlobalScriptFile)});
      foreach(string marker in SceneProbeMarkers) receipt.Markers.Add(marker,false);
      var captured=new List<string>();object gate=new object();int capturedBytes=0;bool outputTruncated=false;
      string outputFile=Path.Combine(plan.ProbeRoot,"logs","probe-observer-output.log");
      receipt.StartedUtc=DateTime.UtcNow.ToString("o");progress("Starte isolierte Szenenprobe: "+plan.ProbeId+" …");
      try {
        using(var sceneRunning=new ManualResetEvent(false))
        using(var process=new Process()) {
          process.StartInfo=new ProcessStartInfo(plan.EngineExecutable,plan.Arguments) {WorkingDirectory=plan.ProbeRoot,UseShellExecute=false,RedirectStandardOutput=true,RedirectStandardError=true,CreateNoWindow=true};
          process.OutputDataReceived+=(sender,args)=>CaptureLine(captured,gate,ref capturedBytes,ref outputTruncated,sceneRunning,"STDOUT",args.Data);
          process.ErrorDataReceived+=(sender,args)=>CaptureLine(captured,gate,ref capturedBytes,ref outputTruncated,sceneRunning,"STDERR",args.Data);
          if(!process.Start()) throw new InvalidOperationException("Die OpenMW-Szenenprobe wurde nicht gestartet.");
          receipt.ProcessStarted=true;process.BeginOutputReadLine();process.BeginErrorReadLine();
          DateTime deadline=DateTime.UtcNow.AddSeconds(maximumSeconds);DateTime? sceneRunningAt=null;
          while(!process.HasExited&&DateTime.UtcNow<deadline) {
            if(!sceneRunningAt.HasValue&&sceneRunning.WaitOne(100)) {
              sceneRunningAt=DateTime.UtcNow;receipt.SceneRunningObservedUtc=sceneRunningAt.Value.ToString("o");
              progress("Szenenmarker beobachtet; halte die lokale Probe "+SceneProbeDwellSeconds+" s im echten Zeitfenster offen …");
            } else Thread.Sleep(100);
            if(sceneRunningAt.HasValue&&DateTime.UtcNow>=sceneRunningAt.Value.AddSeconds(SceneProbeDwellSeconds)&&!process.HasExited) {
              receipt.ControllerStopAfterSceneMarker=true;receipt.ControllerStopRequestedUtc=DateTime.UtcNow.ToString("o");
              StopProbeProcess(process,receipt,"CONTROLLER_CLOSE_AFTER_SCENE_MARKER","CONTROLLER_KILL_AFTER_SCENE_MARKER");
              break;
            }
          }
          if(!process.HasExited&&!receipt.ControllerStopAfterSceneMarker) {
            receipt.WatchdogTriggered=true;receipt.StopMethod="WATCHDOG_CLOSE_MAIN_WINDOW";
            StopProbeProcess(process,receipt,"WATCHDOG_CLOSE_MAIN_WINDOW","WATCHDOG_KILL");
          }
          receipt.ProcessExited=process.HasExited;
          if(receipt.ProcessExited) { process.WaitForExit(); receipt.ProcessExitCode=process.ExitCode; }
        }
      } catch(Exception error) { receipt.ErrorKind=error.GetType().Name; }
      finally {
        lock(gate) File.WriteAllLines(outputFile,captured.ToArray(),Util.Utf8);
        receipt.Logs=ReadProbeLogs(plan.ProbeRoot,receipt.Markers,receipt.UnreadableLogs);
        receipt.FinishedUtc=DateTime.UtcNow.ToString("o");
        if(!receipt.ProcessStarted) receipt.Status="PROCESS_NOT_STARTED";
        else if(receipt.WatchdogTriggered&&!receipt.ProcessExited) receipt.Status="WATCHDOG_STOP_OUTCOME_UNKNOWN";
        else if(receipt.WatchdogTriggered) receipt.Status="WATCHDOG_STOPPED_PROCESS";
        else if(receipt.ControllerStopAfterSceneMarker&&!receipt.ProcessExited) receipt.Status="CONTROLLER_STOP_OUTCOME_UNKNOWN";
        else if(!receipt.ProcessExited) receipt.Status="PROCESS_OUTCOME_UNKNOWN";
        else if(!AllMarkers(receipt.Markers)) receipt.Status="PROCESS_EXITED_MARKERS_INCOMPLETE";
        else if(receipt.ProcessExitCode!=0) receipt.Status="SCENE_MARKERS_WITH_NONZERO_EXIT";
        else if(receipt.ControllerStopAfterSceneMarker) receipt.Status="SCENE_TRANSITION_MARKERS_OBSERVED_CONTROLLER_CLOSED";
        else receipt.Status="SCENE_TRANSITION_MARKERS_OBSERVED";
        WriteSceneProbeReceipt(plan,receipt);progress("Szenenprobe: "+receipt.Status);
      }
      return receipt;
    }
    public void Launch(string id,string tool,Action<string> progress) {
      if(!new[]{"openmw.exe","openmw-launcher.exe","openmw-cs.exe"}.Contains(tool)) throw new InvalidDataException("Unbekanntes Werkzeug.");
      if(DataRoot()==null&&tool=="openmw.exe") throw new InvalidDataException("Für den Spielstart zuerst Morrowind.esm aus einer vollständigen Datenquelle importieren.");
      string runtime=PrepareProfile(id,progress);
      if(tool=="openmw.exe") ValidateLoadOrder(Path.Combine(Root,"profiles",id,"openmw.cfg"));
      Util.Start(Path.Combine(runtime,tool),"",runtime); progress("Gestartet: "+tool+" · "+id);
    }
    public void ValidateLoadOrder(string cfg) {
      string data=DataRoot(); if(data==null) throw new InvalidDataException("Keine Datenquelle.");
      var loaded=new HashSet<string>(StringComparer.OrdinalIgnoreCase);
      foreach(string line in File.ReadAllLines(cfg)) {
        if(!line.StartsWith("content=",StringComparison.Ordinal)) continue;
        string name=line.Substring(8).Trim(); string source=null;
        if(new[]{"Morrowind.esm","Tribunal.esm","Bloodmoon.esm"}.Contains(name,StringComparer.OrdinalIgnoreCase)) source=Path.Combine(data,name);
        else if(String.Equals(name,"LUCINET-World-Reforged.esp",StringComparison.OrdinalIgnoreCase)) source=Path.Combine(ValidateWorldReforged().BasePatch,name);
        else continue;
        var plugin=Inspect.Tes3(source);
        foreach(string master in plugin.Masters) if(!loaded.Contains(master)) throw new InvalidDataException("Master fehlt oder steht zu spät: "+master+" für "+name);
        loaded.Add(name);
      }
      if(!loaded.Contains("Morrowind.esm")) throw new InvalidDataException("Morrowind.esm ist im Profil nicht aktiviert.");
    }
  }
}
