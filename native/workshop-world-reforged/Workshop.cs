using System;
using System.Diagnostics;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Drawing.Imaging;
using System.IO;
using System.Linq;
using System.Threading.Tasks;
using System.Windows.Forms;

namespace Halveth.Morrowind {
  static class Program {
    [STAThread] static int Main(string[] args) {
      Application.EnableVisualStyles(); Application.SetCompatibleTextRenderingDefault(false);
      string root=AppDomain.CurrentDomain.BaseDirectory.TrimEnd('\\');
      try {
        if(args.Length==2&&args[0]=="--render-ui") {
          using(var f=new MainForm(root)) { f.ShowInTaskbar=false; f.StartPosition=FormStartPosition.Manual; f.Location=new Point(-25000,-25000); f.Show(); Application.DoEvents(); using(var image=new Bitmap(f.Width,f.Height)) { f.DrawToBitmap(image,new Rectangle(0,0,f.Width,f.Height)); image.Save(args[1],ImageFormat.Png); } f.Close(); } return 0;
        }
        if(args.Length==2&&args[0]=="--import") { var w=new Workshop(root); var result=w.Import(args[1],s=>Console.WriteLine(s)); Util.Write(Path.Combine(root,"evidence","last-import-cli.json"),result); return 0; }
        if(args.Length==1&&args[0]=="--verify-world-reforged") { var result=new Workshop(root).ValidateWorldReforged(); Util.Write(Path.Combine(root,"evidence","world-reforged-verified-"+Util.Stamp()+".json"),result); Console.WriteLine("World Reforged: Basispatch und Korrekturoverlay geprüft."); return 0; }
        if(args.Length==2&&args[0]=="--prepare") { new Workshop(root).PrepareProfile(args[1],s=>Console.WriteLine(s)); return 0; }
        if(args.Length==2&&args[0]=="--validate-profile") { var w=new Workshop(root); w.PrepareProfile(args[1],s=>Console.WriteLine(s)); w.ValidateLoadOrder(Path.Combine(root,"profiles",args[1],"openmw.cfg")); Util.Write(Path.Combine(root,"evidence","profile-validated-"+Util.Stamp()+".json"),new {profile=args[1],status="LOAD_ORDER_AND_BOUND_WORLD_REFORGED_VALIDATED",recordedUtc=DateTime.UtcNow.ToString("o")}); Console.WriteLine("Profil geprüft: "+args[1]); return 0; }
        if((args.Length==2||args.Length==3)&&args[0]=="--probe-scene") {
          int seconds=25;
          if(args.Length==3&&!Int32.TryParse(args[2],out seconds)) throw new ArgumentException("Die Sekundenangabe der Szenenprobe ist ungültig.");
          var result=new Workshop(root).RunSceneProbe(args[1],seconds,s=>Console.WriteLine(s));
          Console.WriteLine("Szenenprobe: "+result.Status); return result.Status=="SCENE_TRANSITION_MARKERS_OBSERVED"||result.Status=="SCENE_TRANSITION_MARKERS_OBSERVED_CONTROLLER_CLOSED"?0:2;
        }
        if(args.Length==2&&args[0]=="--launch") { new Workshop(root).Launch(args[1],"openmw.exe",s=>Console.WriteLine(s)); return 0; }
        if(args.Length!=0) throw new ArgumentException("Unbekannte Argumente.");
        Application.Run(new MainForm(root)); return 0;
      } catch(Exception e) {
        Directory.CreateDirectory(Path.Combine(root,"evidence")); Util.Write(Path.Combine(root,"evidence","error-"+Util.Stamp()+".json"),new { error=e.ToString(), recordedUtc=DateTime.UtcNow.ToString("o") });
        if(args.Length==0||args[0]=="--launch") MessageBox.Show(e.Message,"Morrowind Workshop",MessageBoxButtons.OK,MessageBoxIcon.Error); else Console.Error.WriteLine(e.ToString()); return 1;
      }
    }
  }
  class Hero : Panel {
    public Hero() { DoubleBuffered=true; }
    protected override void OnPaint(PaintEventArgs e) {
      base.OnPaint(e); var g=e.Graphics; g.SmoothingMode=SmoothingMode.AntiAlias;
      using(var b=new LinearGradientBrush(ClientRectangle,Color.FromArgb(19,35,43),Color.FromArgb(62,40,39),18)) g.FillRectangle(b,ClientRectangle);
      using(var b=new SolidBrush(Color.FromArgb(219,178,113))) g.FillEllipse(b,Width-214,32,108,108);
      using(var b=new SolidBrush(Color.FromArgb(111,123,113))) g.FillEllipse(b,Width-307,59,44,44);
      var ridge=new[]{new Point(Width/3,Height),new Point(Width/2,132),new Point(Width/2+60,155),new Point(Width/2+117,88),new Point(Width/2+220,155),new Point(Width,143),new Point(Width,Height)};
      using(var b=new SolidBrush(Color.FromArgb(30,47,49))) g.FillPolygon(b,ridge);
      for(int i=0;i<8;i++) {
        int x=Width-43-i*46,y=Height-30-(i%3)*18; using(var b=new SolidBrush(Color.FromArgb(32,25,26))) { g.FillRectangle(b,x,y-13,5,Height-y+13); g.FillEllipse(b,x-18,y-24,41,16); }
      }
      using(var small=new Font("Segoe UI",9,FontStyle.Bold)) using(var big=new Font("Georgia",31)) using(var sub=new Font("Segoe UI",12)) {
        g.DrawString("HALVETH  /  WORLD REFORGED CANDIDATE 0.4.1",small,Brushes.BurlyWood,29,24);
        g.DrawString("Morrowind\nWorkshop",big,Brushes.AntiqueWhite,25,49);
        g.DrawString("Eigene Laufzeit. Eigene Weltvorschau.",sub,Brushes.LightGray,29,169);
      }
    }
  }
  public class MainForm : Form {
    readonly Workshop workshop;
    readonly Color ink=Color.FromArgb(229,226,214),muted=Color.FromArgb(170,180,180),panelColor=Color.FromArgb(29,36,40);
    Label headline,details,log;
    ComboBox profile;
    Button play,import,sceneProbe;
    FlowLayoutPanel actions;
    TextBox inventory;
    bool busy;
    public MainForm(string root) {
      workshop=new Workshop(root); Text="HALVETH · Morrowind Workshop · World Reforged Candidate 0.4.1"; BackColor=Color.FromArgb(19,25,29); ForeColor=ink;
      Font=new Font("Segoe UI",10); ClientSize=new Size(1220,940); MinimumSize=new Size(1090,900); StartPosition=FormStartPosition.CenterScreen;
      AutoScaleMode=AutoScaleMode.Dpi;
      var grid=new TableLayoutPanel { Dock=DockStyle.Fill, ColumnCount=1,RowCount=5,Padding=new Padding(24),BackColor=BackColor };
      grid.RowStyles.Add(new RowStyle(SizeType.Absolute,218)); grid.RowStyles.Add(new RowStyle(SizeType.Absolute,114)); grid.RowStyles.Add(new RowStyle(SizeType.Absolute,62)); grid.RowStyles.Add(new RowStyle(SizeType.Percent,100)); grid.RowStyles.Add(new RowStyle(SizeType.Absolute,35));
      Controls.Add(grid);
      grid.Controls.Add(new Hero {Dock=DockStyle.Fill,Margin=new Padding(0,0,0,12)},0,0);
      var status=new Panel {Dock=DockStyle.Fill,BackColor=panelColor,Padding=new Padding(18),Margin=new Padding(0,0,0,10)};
      headline=new Label {Location=new Point(18,12),AutoSize=true,Font=new Font("Segoe UI",14,FontStyle.Bold),ForeColor=Color.FromArgb(230,191,130)};
      details=new Label {Location=new Point(18,44),Size=new Size(990,52),Anchor=AnchorStyles.Left|AnchorStyles.Right|AnchorStyles.Top,ForeColor=muted};
      status.Controls.Add(headline);status.Controls.Add(details);grid.Controls.Add(status,0,1);
      actions=new FlowLayoutPanel {Dock=DockStyle.Fill,WrapContents=false,Margin=new Padding(0)};
      import=Btn("1  Spieldaten importieren",225,()=>Import()); actions.Controls.Add(import);
      profile=new ComboBox {DropDownStyle=ComboBoxStyle.DropDownList,Width=246,Height=38,Margin=new Padding(8,6,8,0),BackColor=panelColor,ForeColor=ink,Font=new Font("Segoe UI",11)};
      profile.Items.AddRange(Workshop.ProfileNames); profile.SelectedIndex=Array.IndexOf(Workshop.ProfileIds,workshop.State.Profile); actions.Controls.Add(profile);
      play=Btn("2  Morrowind starten",224,()=>Launch("openmw.exe")); play.BackColor=Color.FromArgb(193,146,80); play.ForeColor=Color.FromArgb(20,25,29); actions.Controls.Add(play);
      sceneProbe=Btn("Szenenprobe · 25 s",202,()=>Probe()); sceneProbe.BackColor=Color.FromArgb(69,116,126); actions.Controls.Add(sceneProbe);
      actions.Controls.Add(Btn("Editor öffnen",172,()=>Launch("openmw-cs.exe"))); grid.Controls.Add(actions,0,2);
      var tabs=new TabControl {Dock=DockStyle.Fill,Font=new Font("Segoe UI",10),Padding=new Point(18,7)};
      grid.Controls.Add(tabs,0,3);
      var overview=Page(tabs,"Spiel & Grafik");
      var layout=new TableLayoutPanel {Dock=DockStyle.Fill,ColumnCount=2,RowCount=3,Padding=new Padding(12)};
      for(int i=0;i<2;i++)layout.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,50));
      layout.RowStyles.Add(new RowStyle(SizeType.Percent,50));layout.RowStyles.Add(new RowStyle(SizeType.Percent,50));layout.RowStyles.Add(new RowStyle(SizeType.Absolute,55));overview.Controls.Add(layout);
      layout.Controls.Add(Card("KLASSIK", "OpenMW mit Originaldaten", "Kurze Sichtweite, dezente Grafik.\n\nStory, Quests und Spielregeln kommen aus deinem Datenstand. OpenMW ist eine eigene Engine; die alte EXE bleibt ein eigener historischer Stand."),0,0);
      layout.Controls.Add(Card("WEITSICHT", "Dein Startprofil", "Weites Gelände, 16× Texturfilter, 4× Kantenglättung, Wasserreflexionen und Schatten.\n\nKeine pauschalen Änderungen an Gold, NPCs oder Questbelohnungen."),1,0);
      layout.Controls.Add(Card("ULTRA", "Zum Vergleichen", "Noch mehr Sichtweite und Schattenreichweite. Eigene Einstellungen und Spielstände.\n\nHohe Last ist möglich. Die passende Stufe entscheidet sich im Spiel, besonders in Vivec."),0,1);
      layout.Controls.Add(Card("WELT REFORGED", "Genesis-Erweiterung geladen", "Basispatch, Korrekturoverlay und die eigene HALVETH-Spielschicht werden vor dem Start gegen ihre Manifeste geprüft.\n\nWissen, Weltleben, Perspektive, eigene Bücher und Zauber sowie der Atmosphärenfilter bleiben im getrennten Profil. Die bestehende 0.2.0-Installation bleibt unverändert."),1,1);
      var overviewActions=new FlowLayoutPanel {Dock=DockStyle.Fill,WrapContents=false,Margin=new Padding(4,0,4,0)};
      overviewActions.Controls.Add(Btn("Grafik & Mod-Ladereihenfolge",305,()=>Launch("openmw-launcher.exe")));
      overviewActions.Controls.Add(Btn("Profilordner öffnen",250,()=>OpenProfile()));
      overviewActions.Controls.Add(Btn("Kandidatenordner öffnen",250,()=>OpenFolder(workshop.Root)));
      layout.Controls.Add(overviewActions,0,2);layout.SetColumnSpan(overviewActions,2);
      var assets=Page(tabs,"Dateien & Musik");
      inventory=new TextBox {Dock=DockStyle.Fill,Multiline=true,ReadOnly=true,ScrollBars=ScrollBars.Vertical,BackColor=panelColor,ForeColor=ink,BorderStyle=BorderStyle.None,Font=new Font("Consolas",10)}; assets.Padding=new Padding(18);assets.Controls.Add(inventory);
      var original=Page(tabs,"Original & Eigenheiten"); original.Padding=new Padding(20);
      original.Controls.Add(new Label {Dock=DockStyle.Fill,ForeColor=ink,Text="ERHALTUNGS- UND KANDIDATENVERTRAG\n\n• Originalquellen werden als eigene Datenkopien mit SHA-256-Receipt übernommen.\n• Jedes Profil hat eigene Spielstände. Andere Installationen behalten ihre Einstellungen.\n• Welt Reforged liegt zusätzlich als gebundener lokaler Basispatch plus Korrekturoverlay vor.\n• Die eigene HALVETH-Spielschicht lädt getrennt: Wissen, Weltleben, Perspektive, Bücher, Zauber und Lichtfilter.\n• Alle drei lokalen Bindungen werden vor der Konfiguration über SHA-256 und Manifestdateien geprüft.\n• Die bestehende 0.2.0-Installation bleibt ein eigener historischer Stand.\n\nOpenMW verbessert die Laufzeit. Ein ungepatchtes Morrowind.exe und dessen Verhalten sind ein eigener Referenzstand.\nEin Text- oder Hashspiegel kann fehlende Originaldateien nicht wiederherstellen.",Font=new Font("Segoe UI",11)});
      var build=Page(tabs,"Welt bauen");build.Padding=new Padding(20);
      var info=new Label {Dock=DockStyle.Top,Height=176,Text="NATIVER WELT- UND INHALTSEDITOR\n\nOpenMW-CS ist enthalten. Damit lassen sich eigene Zellen, NPCs, Gegenstände, Dialoge und Quests anlegen.\nWähle im Editor die vorhandenen Masterdateien und erzeuge ein neues Add-on. Die Ausgaben gehören in den\nData-Ordner des aktiven Profils. Aktiviere das Add-on anschließend im OpenMW-Launcher.\n\nTamriel Rebuilt benötigt eigene vollständige Pakete plus Tribunal und Bloodmoon. MGE XE/MWSE verwenden\nden klassischen Engine-Zweig und werden hier nicht als OpenMW-Erweiterungen aktiviert."};build.Controls.Add(info);
      var builderActions=new FlowLayoutPanel {Dock=DockStyle.Bottom,Height=54};builderActions.Controls.Add(Btn("OpenMW-CS öffnen",220,()=>Launch("openmw-cs.exe")));builderActions.Controls.Add(Btn("Mod-Ordner öffnen",220,()=>OpenFolder(Path.Combine(workshop.Root,"mods"))));build.Controls.Add(builderActions);
      log=new Label {Dock=DockStyle.Fill,TextAlign=ContentAlignment.MiddleLeft,ForeColor=muted,Text="Native Windows-Anwendung · OpenMW 0.51.0 · lokale Profile"};grid.Controls.Add(log,0,4);
      RefreshStatus();
    }
    TabPage Page(TabControl tabs,string title) { var page=new TabPage(title) {BackColor=panelColor,ForeColor=ink}; tabs.TabPages.Add(page);return page; }
    Panel Card(string kicker,string title,string body) {
      var p=new Panel {Dock=DockStyle.Fill,Padding=new Padding(12),Margin=new Padding(4),BackColor=panelColor};
      p.Controls.Add(new Label {Dock=DockStyle.Fill,Text=body,ForeColor=muted,Font=new Font("Segoe UI",10)});
      p.Controls.Add(new Label {Dock=DockStyle.Top,Height=42,Text=title,Font=new Font("Segoe UI",13,FontStyle.Bold)});
      p.Controls.Add(new Label {Dock=DockStyle.Top,Height=29,Text=kicker,ForeColor=Color.FromArgb(218,175,109),Font=new Font("Segoe UI",9,FontStyle.Bold)});return p;
    }
    Button Btn(string text,int width,Action click) {var b=new Button {Text=text,Width=width,Height=40,FlatStyle=FlatStyle.Flat,BackColor=Color.FromArgb(46,57,62),ForeColor=ink,Margin=new Padding(0,0,8,0),Cursor=Cursors.Hand};b.FlatAppearance.BorderColor=Color.FromArgb(75,86,86);b.Click+=(s,e)=>click();return b;}
    string Profile() {return Workshop.ProfileIds[profile.SelectedIndex];}
    void Progress(string text) { if(IsDisposed)return; if(InvokeRequired) BeginInvoke(new Action<string>(Progress),text);else log.Text=text; }
    async void Run(Action work) { if(busy)return;busy=true;actions.Enabled=false; try {await Task.Run(work); RefreshStatus();}catch(Exception e){Progress("Aktion angehalten: "+e.Message);MessageBox.Show(this,e.Message,"Morrowind Workshop",MessageBoxButtons.OK,MessageBoxIcon.Information);}finally{actions.Enabled=true;busy=false;} }
    void Import() {using(var dialog=new OpenFileDialog {Title="Morrowind.esm aus einer vollständigen Installation auswählen",Filter="Morrowind.esm|Morrowind.esm",CheckFileExists=true}) if(dialog.ShowDialog(this)==DialogResult.OK){string file=dialog.FileName;Run(()=>workshop.Import(file,Progress));}}
    void Launch(string tool) {string id=Profile();Run(()=>workshop.Launch(id,tool,Progress));}
    void Probe() {string id=Profile();Run(()=>workshop.RunSceneProbe(id,25,Progress));}
    void OpenFolder(string path) { Directory.CreateDirectory(path); Process.Start(new ProcessStartInfo("explorer.exe",Util.Arg(path)) {UseShellExecute=false}); }
    void OpenProfile() {OpenFolder(Path.Combine(workshop.Root,"profiles",Profile()));}
    void RefreshStatus() {
      var r=workshop.Receipt(); play.Enabled=r!=null;sceneProbe.Enabled=r!=null;
      if(r==null) {
        headline.Text="Engine & Editor bereit · Spieldaten noch verbinden";
        details.Text="Wähle Morrowind.esm aus deinen vollständigen Data Files. Musik, Sounds und Archive werden mitkopiert.\nDie ursprüngliche Quelle bleibt erhalten.";
        inventory.Text="NOCH KEIN DATENIMPORT\r\n\r\nDie Werkstatt enthält OpenMW und den Editor.\r\nNPCs, Welt, Dialoge und Originalmusik werden aus deinen Data Files gelesen.\r\n\r\nEin .crdownload oder ein Video-Preview ist noch keine bestätigte vollständige Spieldatenquelle.\r\nDer Import prüft ESM/BSA-Strukturen und kopiert jede Datei mit SHA-256-Prüfung.";
      } else {
        headline.Text="Datenkopie bereit · "+r.Files.Count.ToString("N0")+" Dateien erhalten";
        details.Text="Morrowind, Tribunal und Bloodmoon mit Musik und Sounds aus deiner Datenkopie.\nWähle ein Profil und starte das Spiel. Jeder Datenstand hat eigene Spielstände.";
        import.Text="Datenstand wechseln";
        play.Text="Morrowind starten";
        var b=new System.Text.StringBuilder(); b.AppendLine("IMPORT  "+r.Id);b.AppendLine("DATEIEN "+r.Files.Count+"  /  "+(r.Files.Sum(f=>f.Bytes)/1048576.0).ToString("N1")+" MiB");
        foreach(var plugin in r.Plugins){b.AppendLine();b.AppendLine(plugin.FileName+" · "+plugin.Count+" Datensätze");foreach(string key in new[]{"NPC_","CELL","LAND","DIAL","INFO","SCPT","SOUN"})if(plugin.Records.ContainsKey(key))b.AppendLine("  "+key+"  "+plugin.Records[key]);}
        b.AppendLine();foreach(var a in r.Archives)b.AppendLine(a.Key+" · "+a.Value.Files+" Archivdateien");
        b.AppendLine();foreach(var c in r.LooseAssets.Categories)b.AppendLine(c.Key+" · "+c.Value+" lose Dateien");b.AppendLine();foreach(string w in r.Warnings)b.AppendLine(w);inventory.Text=b.ToString();
      }
    }
  }
}
