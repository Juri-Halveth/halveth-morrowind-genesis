using System.Diagnostics;
using System.IO.Compression;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Windows.Forms;

namespace Halveth.Genesis.Setup;

internal sealed class PayloadFile
{
    public string path { get; set; } = "";
    public string sha256 { get; set; } = "";
    public long bytes { get; set; }
}

internal sealed class PayloadManifest
{
    public string version { get; set; } = "";
    public string mode { get; set; } = "";
    public string pythonSha256 { get; set; } = "";
    public string? engineSource { get; set; }
    public List<PayloadFile> files { get; set; } = new();
}

internal sealed class InstalledState
{
    public string version { get; set; } = "";
    public string mode { get; set; } = "";
    public string installedUtc { get; set; } = "";
    public string engineRoot { get; set; } = "";
    public string sourceProfile { get; set; } = "";
    public string? gameData { get; set; }
    public string[] shortcuts { get; set; } = Array.Empty<string>();
    public Dictionary<string, string> shortcutBackups { get; set; } = new();
    public List<PayloadFile> files { get; set; } = new();
}

internal static class Program
{
    private const string Title = "HALVETH · Morrowind Genesis";
    private const string InstalledExe = "HALVETH Morrowind.exe";
    private const string InstalledStateFile = "install-state.json";
    private static readonly JsonSerializerOptions JsonOptions = new() { WriteIndented = true };

    [STAThread]
    private static int Main(string[] args)
    {
        try
        {
            string selfTarget = File.Exists(Path.Combine(AppContext.BaseDirectory, InstalledStateFile))
                ? AppContext.BaseDirectory : DefaultTarget();
            string target = Option(args, "--target") ?? selfTarget;
            if (args.Contains("--install"))
            {
                string engine = Option(args, "--engine-root") ?? DefaultEngineRoot();
                string source = Option(args, "--source-profile") ?? Path.Combine(engine, "profiles", "max");
                var receipt = Install(target, engine, source, args.Contains("--no-shortcuts"),
                    args.Contains("--consolidate-shortcuts"), Option(args, "--game-data"));
                Console.WriteLine(JsonSerializer.Serialize(receipt, JsonOptions));
                return 0;
            }
            if (args.Contains("--check"))
            {
                var (passed, receipt) = Check(target);
                Console.WriteLine(JsonSerializer.Serialize(receipt, JsonOptions));
                return passed ? 0 : 1;
            }
            if (args.Contains("--play"))
            {
                Play(target);
                return 0;
            }
            if (args.Contains("--uninstall"))
            {
                var (complete, receipt) = Uninstall(target);
                Console.WriteLine(JsonSerializer.Serialize(receipt, JsonOptions));
                return complete ? 0 : 1;
            }
            if (args.Length > 0) throw new ArgumentException("Unbekannter Aufruf. Nutze --install, --check, --play oder --uninstall.");
            var current = Path.Combine(AppContext.BaseDirectory, InstalledStateFile);
            if (File.Exists(current))
            {
                Play(AppContext.BaseDirectory);
                return 0;
            }
            ApplicationConfiguration.Initialize();
            Application.Run(new InstallerForm());
            return 0;
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine(ex.ToString());
            if (Environment.UserInteractive && !Console.IsErrorRedirected)
                MessageBox.Show(ex.Message, Title, MessageBoxButtons.OK, MessageBoxIcon.Error);
            return 1;
        }
    }

    private static string? Option(string[] args, string name)
    {
        int index = Array.IndexOf(args, name);
        if (index < 0) return null;
        if (index + 1 >= args.Length || args[index + 1].StartsWith("--"))
            throw new ArgumentException($"{name} benötigt einen Pfad.");
        return args[index + 1];
    }

    internal static string DefaultTarget() => Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "HALVETH", "Morrowind Genesis");
    internal static string DefaultEngineRoot() => Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "HALVETH", "Morrowind-Native", "0.2.0");

    private static string Absolute(string path)
    {
        if (string.IsNullOrWhiteSpace(path)) throw new ArgumentException("Ein Pfad fehlt.");
        string full = Path.GetFullPath(path);
        if (Path.GetPathRoot(full) == full || full == Environment.GetFolderPath(Environment.SpecialFolder.UserProfile))
            throw new ArgumentException("Installationsziel darf kein Laufwerks- oder Benutzerstamm sein.");
        return full.TrimEnd(Path.DirectorySeparatorChar);
    }

    private static void VerifySource(string engineRoot, string sourceProfile)
    {
        foreach (string path in new[] {
            Path.Combine(engineRoot, "engine", "openmw.exe"),
            Path.Combine(engineRoot, "engine", "resources"),
            Path.Combine(sourceProfile, "openmw.cfg"),
            Path.Combine(sourceProfile, "settings.cfg") })
        {
            if (!File.Exists(path) && !Directory.Exists(path))
                throw new FileNotFoundException("Die Morrowind/OpenMW-Quelle fehlt: " + path);
        }
        // A user-owned Morrowind data tree is required; never embed or copy it.
        string cfg = File.ReadAllText(Path.Combine(sourceProfile, "openmw.cfg"), Encoding.UTF8);
        if (!cfg.Split('\n').Any(line => line.TrimStart().StartsWith("content=Morrowind.esm", StringComparison.OrdinalIgnoreCase)))
            throw new InvalidDataException("Das gewählte Profil lädt Morrowind.esm nicht.");
        bool gameData = false;
        foreach (string line in cfg.Split('\n'))
        {
            if (!line.TrimStart().StartsWith("data=", StringComparison.OrdinalIgnoreCase)) continue;
            string dataPath = Unquote(line[(line.IndexOf('=') + 1)..]);
            string resolved = Path.GetFullPath(Path.IsPathRooted(dataPath)
                ? dataPath : Path.Combine(sourceProfile, dataPath));
            if (File.Exists(Path.Combine(resolved, "Morrowind.esm"))) { gameData = true; break; }
        }
        if (!gameData) throw new InvalidDataException("Morrowind.esm wurde in den eingebundenen Spieldaten nicht gefunden.");
    }

    private static string VerifyGameData(string path)
    {
        string full = Absolute(path);
        if (!Directory.Exists(full) || !File.Exists(Path.Combine(full, "Morrowind.esm")) ||
            !File.Exists(Path.Combine(full, "Morrowind.bsa")))
            throw new FileNotFoundException("Der eigene Morrowind-Ordner braucht Morrowind.esm und Morrowind.bsa: " + full);
        return full;
    }

    private static (ZipArchive zip, PayloadManifest manifest) OpenPayload()
    {
        Stream stream = Assembly.GetExecutingAssembly().GetManifestResourceStream("GenesisPayload")
            ?? throw new InvalidDataException("Installationsdaten fehlen in der EXE.");
        var zip = new ZipArchive(stream, ZipArchiveMode.Read, false);
        ZipArchiveEntry manifestEntry = zip.GetEntry("payload-manifest.json")
            ?? throw new InvalidDataException("Paketmanifest fehlt.");
        PayloadManifest manifest;
        using (var reader = new StreamReader(manifestEntry.Open(), Encoding.UTF8))
            manifest = JsonSerializer.Deserialize<PayloadManifest>(reader.ReadToEnd())
                ?? throw new InvalidDataException("Paketmanifest ist unlesbar.");
        if (manifest.version.Length == 0 || manifest.mode is not ("owned-mod" or "local-engine"))
            throw new InvalidDataException("Paketmodus oder Version ist ungültig.");
        var expected = manifest.files.Select(item => item.path).ToHashSet(StringComparer.Ordinal);
        var actual = zip.Entries.Where(entry => entry.Name.Length > 0 && entry.FullName != "payload-manifest.json")
            .Select(entry => entry.FullName).ToHashSet(StringComparer.Ordinal);
        if (expected.Count != manifest.files.Count || !expected.SetEquals(actual))
            throw new InvalidDataException("Dateiliste und Installationsdaten stimmen nicht überein.");
        bool hasEngine = manifest.files.Any(item => item.path == "engine/openmw.exe");
        if (hasEngine != (manifest.mode == "local-engine"))
            throw new InvalidDataException("Enginepaket und Modus widersprechen sich.");
        return (zip, manifest);
    }

    private static string Sha256(string path)
    {
        using var input = File.OpenRead(path);
        return Convert.ToHexString(SHA256.HashData(input)).ToLowerInvariant();
    }

    private static string Within(string root, string relative)
    {
        if (relative.Contains('\\') || relative.StartsWith('/') || relative.Contains(':') ||
            relative.Split('/').Any(part => part is "" or "." or ".."))
            throw new InvalidDataException("Ungültiger Paketpfad: " + relative);
        string full = Path.GetFullPath(Path.Combine(root, relative.Replace('/', Path.DirectorySeparatorChar)));
        if (!full.StartsWith(root.TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar,
            StringComparison.OrdinalIgnoreCase))
            throw new InvalidDataException("Paketpfad verlässt das Ziel: " + relative);
        return full;
    }

    private static bool HasLinkedParent(string root, string relative)
    {
        string current = root;
        string[] parts = relative.Split('/');
        for (int i = 0; i < parts.Length - 1; i++)
        {
            current = Path.Combine(current, parts[i]);
            if (Directory.Exists(current) && (File.GetAttributes(current) & FileAttributes.ReparsePoint) != 0)
                return true;
        }
        return false;
    }

    private static void Extract(ZipArchive zip, PayloadManifest manifest, string stage)
    {
        foreach (PayloadFile file in manifest.files)
        {
            ZipArchiveEntry entry = zip.GetEntry(file.path)
                ?? throw new InvalidDataException("Paketdatei fehlt: " + file.path);
            if (entry.Length != file.bytes) throw new InvalidDataException("Dateigröße weicht ab: " + file.path);
            string output = Within(stage, file.path);
            Directory.CreateDirectory(Path.GetDirectoryName(output)!);
            using (Stream source = entry.Open())
            using (FileStream destination = File.Create(output)) source.CopyTo(destination);
            if (Sha256(output) != file.sha256)
                throw new InvalidDataException("Prüfsumme weicht ab: " + file.path);
        }
    }

    private static string Unquote(string value) => value.Trim().Trim('"').Replace("&&", "&").Replace("&\"", "\"");

    private static string AbsolutizeConfigPath(string value, string sourceProfile)
    {
        string raw = Unquote(value);
        if (raw.Contains('?')) throw new InvalidDataException("Ungenutzter OpenMW-Pfadplatzhalter: " + raw);
        string full = Path.GetFullPath(Path.IsPathRooted(raw) ? raw : Path.Combine(sourceProfile, raw));
        return "\"" + full.Replace('\\', '/').Replace("&", "&&").Replace("\"", "&\"") + "\"";
    }

    private static List<PayloadFile> CreatePrivateProfile(string stage, string sourceProfile)
    {
        string output = Path.Combine(stage, "profiles", "max");
        Directory.CreateDirectory(output);
        var lines = new List<string>();
        foreach (string line in File.ReadAllLines(Path.Combine(sourceProfile, "openmw.cfg")))
        {
            int equal = line.IndexOf('=');
            if (equal < 0) { lines.Add(line); continue; }
            string key = line[..equal].Trim();
            string value = line[(equal + 1)..];
            lines.Add(key is "data" or "user-data" or "data-local" or "config"
                ? key + "=" + AbsolutizeConfigPath(value, sourceProfile) : line);
        }
        File.WriteAllLines(Path.Combine(output, "openmw.cfg"), lines, new UTF8Encoding(false));
        File.Copy(Path.Combine(sourceProfile, "settings.cfg"), Path.Combine(output, "settings.cfg"));
        return new[] { "profiles/max/openmw.cfg", "profiles/max/settings.cfg" }
            .Select(path => new PayloadFile { path = path, bytes = new FileInfo(Within(stage, path)).Length,
                sha256 = Sha256(Within(stage, path)) }).ToList();
    }

    private static List<PayloadFile> CreatePrivateProfileFromGameData(string stage, string gameData)
    {
        string output = Path.Combine(stage, "profiles", "max");
        Directory.CreateDirectory(output);
        var lines = new List<string> { "# Licensed Morrowind files remain at their original location.",
            "encoding=win1252", "data=\"" + gameData.Replace('\\', '/').Replace("&", "&&") + "\"",
            "fallback-archive=Morrowind.bsa", "content=Morrowind.esm" };
        foreach (string expansion in new[] { "Tribunal", "Bloodmoon" })
        {
            if (File.Exists(Path.Combine(gameData, expansion + ".esm")) &&
                File.Exists(Path.Combine(gameData, expansion + ".bsa")))
            {
                lines.Add("fallback-archive=" + expansion + ".bsa");
                lines.Add("content=" + expansion + ".esm");
            }
        }
        File.WriteAllLines(Path.Combine(output, "openmw.cfg"), lines, new UTF8Encoding(false));
        File.WriteAllText(Path.Combine(output, "settings.cfg"), "[Video]\nresolution x = 1280\nresolution y = 720\n", new UTF8Encoding(false));
        return new[] { "profiles/max/openmw.cfg", "profiles/max/settings.cfg" }
            .Select(path => new PayloadFile { path = path, bytes = new FileInfo(Within(stage, path)).Length,
                sha256 = Sha256(Within(stage, path)) }).ToList();
    }

    internal static object Install(string rawTarget, string rawEngineRoot, string rawSourceProfile,
        bool noShortcuts, bool consolidateShortcuts, string? rawGameData)
    {
        if (!Environment.Is64BitOperatingSystem)
            throw new PlatformNotSupportedException("Dieses Paket benötigt 64-Bit-Windows.");
        string target = Absolute(rawTarget);
        string externalEngine = Absolute(rawEngineRoot);
        string sourceProfile = Absolute(rawSourceProfile);
        if (target.Equals(externalEngine, StringComparison.OrdinalIgnoreCase) ||
            target.StartsWith(externalEngine + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase))
            throw new IOException("Installationsziel darf nicht innerhalb der vorhandenen Engine liegen.");
        if (Directory.Exists(target) && (File.GetAttributes(target) & FileAttributes.ReparsePoint) != 0)
            throw new IOException("Installationsziel darf kein Link oder Junction sein.");
        if (Directory.Exists(target) && Directory.EnumerateFileSystemEntries(target).Any())
            throw new IOException("Das Installationsziel ist bereits belegt. Persönliche Daten werden nicht überschrieben: " + target);
        if (File.Exists(target)) throw new IOException("Installationsziel ist eine Datei: " + target);
        var (zip, manifest) = OpenPayload();
        using (zip)
        {
            string? gameData = string.IsNullOrWhiteSpace(rawGameData) ? null : VerifyGameData(rawGameData);
            if (gameData is not null && manifest.mode != "local-engine")
                throw new InvalidOperationException("--game-data benötigt die lokale Voll-Engine-Variante.");
            if (gameData is null) VerifySource(externalEngine, sourceProfile);
            if (gameData is not null && (target.Equals(gameData, StringComparison.OrdinalIgnoreCase) ||
                target.StartsWith(gameData + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase)))
                throw new IOException("Die Installation darf nicht in die ursprünglichen Spieldaten schreiben.");
            string parent = Path.GetDirectoryName(target)!;
            Directory.CreateDirectory(parent);
            string stage = target + ".staging-" + Guid.NewGuid().ToString("N");
            Directory.CreateDirectory(stage);
            bool moved = false;
            try
            {
                Extract(zip, manifest, stage);
                var installedFiles = new List<PayloadFile>(manifest.files);
                string engineRoot = manifest.mode == "local-engine" ? target : externalEngine;
                if (manifest.mode == "local-engine")
                    installedFiles.AddRange(gameData is null
                        ? CreatePrivateProfile(stage, sourceProfile)
                        : CreatePrivateProfileFromGameData(stage, gameData));
                string self = Environment.ProcessPath ?? throw new IOException("Installationsprogramm-Pfad fehlt.");
                string entry = Path.Combine(stage, InstalledExe);
                File.Copy(self, entry);
                installedFiles.Add(new PayloadFile { path = InstalledExe, bytes = new FileInfo(entry).Length,
                    sha256 = Sha256(entry) });
                string python = Path.Combine(stage, "runtime", "python.exe");
                using (var preflight = Process.Start(new ProcessStartInfo(python,
                    "-c \"import sqlite3, ssl, json, urllib.request; print('HALVETH_PYTHON_OK')\"")
                { UseShellExecute = false, CreateNoWindow = true, RedirectStandardOutput = true, RedirectStandardError = true,
                    WorkingDirectory = stage }))
                {
                    if (preflight is null || !preflight.WaitForExit(15000) || preflight.ExitCode != 0 ||
                        !preflight.StandardOutput.ReadToEnd().Contains("HALVETH_PYTHON_OK"))
                        throw new IOException("Private Python-Laufzeit konnte nicht gestartet werden.");
                }
                var state = new InstalledState { version = manifest.version, mode = manifest.mode,
                    installedUtc = DateTimeOffset.UtcNow.ToString("O"), engineRoot = engineRoot,
                    sourceProfile = gameData is null ? sourceProfile : "", gameData = gameData,
                    files = installedFiles };
                File.WriteAllText(Path.Combine(stage, InstalledStateFile), JsonSerializer.Serialize(state, JsonOptions), Encoding.UTF8);
                if (Directory.Exists(target)) Directory.Delete(target); // verified empty above
                Directory.Move(stage, target);
                moved = true;
                var shortcuts = noShortcuts ? (Array.Empty<string>(), new Dictionary<string, string>())
                    : CreateShortcuts(target, consolidateShortcuts);
                state.shortcuts = shortcuts.Item1;
                state.shortcutBackups = shortcuts.Item2;
                File.WriteAllText(Path.Combine(target, InstalledStateFile), JsonSerializer.Serialize(state, JsonOptions), Encoding.UTF8);
                return new { status = "INSTALLED", mode = state.mode, version = state.version,
                    target, engineRoot, gameDataMode = gameData is not null, python = "embedded-3.14.7", files = installedFiles.Count,
                    shortcutCount = state.shortcuts.Length, shortcutBackups = state.shortcutBackups.Count,
                    state = Path.Combine(target, InstalledStateFile) };
            }
            finally
            {
                if (!moved && Directory.Exists(stage)) Directory.Delete(stage, true);
            }
        }
    }

    private static InstalledState ReadState(string target)
    {
        if (Directory.Exists(target) && (File.GetAttributes(target) & FileAttributes.ReparsePoint) != 0)
            throw new IOException("Installationsziel ist jetzt ein Link oder Junction.");
        string file = Path.Combine(target, InstalledStateFile);
        InstalledState state = JsonSerializer.Deserialize<InstalledState>(File.ReadAllText(file, Encoding.UTF8))
            ?? throw new InvalidDataException("Installationsstand ist unlesbar.");
        if (state.version.Length == 0 || state.mode is not ("owned-mod" or "local-engine"))
            throw new InvalidDataException("Installationsstand ist ungültig.");
        return state;
    }

    private static (bool, object) Check(string rawTarget)
    {
        string target = Absolute(rawTarget);
        InstalledState state = ReadState(target);
        var broken = state.files.Where(file => HasLinkedParent(target, file.path) ||
            !File.Exists(Within(target, file.path)) ||
            (file.path != "app/mod/bridge/inbox.json" &&
             Sha256(Within(target, file.path)) != file.sha256)).Select(file => file.path).ToArray();
        bool engine = File.Exists(Path.Combine(state.engineRoot, "engine", "openmw.exe"));
        bool passed = broken.Length == 0 && engine;
        return (passed, new { status = passed ? "PASS" : "FAIL", mode = state.mode,
            state.version, target, engine, broken });
    }

    private static void Play(string rawTarget)
    {
        string target = Absolute(rawTarget);
        InstalledState state = ReadState(target);
        string engine = Path.Combine(state.engineRoot, "engine", "openmw.exe");
        string python = Path.Combine(target, "runtime", "python.exe");
        string launcher = Path.Combine(target, "app", "launcher.py");
        foreach (string required in new[] { engine, python, launcher, Path.Combine(target, "app", "mod", "halveth.omwscripts") })
            if (!File.Exists(required)) throw new FileNotFoundException("Spieldatei fehlt: " + required);
        var start = new ProcessStartInfo(python)
        { UseShellExecute = false, CreateNoWindow = true, WorkingDirectory = Path.Combine(target, "app") };
        start.ArgumentList.Add(launcher);
        start.ArgumentList.Add("--play");
        start.ArgumentList.Add("--profile");
        start.ArgumentList.Add("beauty");
        start.Environment["HALVETH_MORROWIND_INSTALL_ROOT"] = state.engineRoot;
        using Process process = Process.Start(start) ?? throw new IOException("Spieleinstieg konnte nicht starten.");
        process.WaitForExit();
        if (process.ExitCode != 0)
            throw new IOException("Morrowind konnte nicht starten. Einzelheiten stehen in app/.local/companion-start-errors.log.");
    }

    private static (bool, object) Uninstall(string rawTarget)
    {
        string target = Absolute(rawTarget);
        InstalledState state = ReadState(target);
        var retained = new List<string>();
        int removed = 0;
        foreach (PayloadFile file in state.files)
        {
            string path = Within(target, file.path);
            if (HasLinkedParent(target, file.path)) { retained.Add(file.path); continue; }
            if (!File.Exists(path)) continue;
            if (Sha256(path) != file.sha256) { retained.Add(file.path); continue; }
            try { File.Delete(path); removed++; }
            catch (IOException) { retained.Add(file.path); }
            catch (UnauthorizedAccessException) { retained.Add(file.path); }
        }
        foreach (string shortcut in state.shortcuts)
        {
            if (!File.Exists(shortcut)) continue;
            try
            {
                dynamic shell = Activator.CreateInstance(Type.GetTypeFromProgID("WScript.Shell")!)!;
                dynamic link = shell.CreateShortcut(shortcut);
                string current = (string)link.TargetPath;
                if (string.Equals(Path.GetFullPath(current), Path.Combine(target, InstalledExe), StringComparison.OrdinalIgnoreCase))
                {
                    if (state.shortcutBackups.TryGetValue(shortcut, out string? backup) && File.Exists(backup)
                        && Path.GetFullPath(backup).StartsWith(Path.Combine(target, "shortcut-backups") +
                            Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase))
                    {
                        File.Copy(backup, shortcut, true);
                        File.Delete(backup);
                    }
                    else File.Delete(shortcut);
                }
            }
            catch { /* A changed shortcut belongs to the user. */ }
        }
        // User saves, conversation memory, graphics settings and modified files survive.
        // Keep the manifest when Windows locks the running installed EXE, or a
        // user has edited an installed file. A later setup run can then retry
        // exact-file cleanup; it must never strand files without a receipt.
        bool complete = retained.Count == 0;
        if (complete) File.Delete(Path.Combine(target, InstalledStateFile));
        var ownedDirectories = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        foreach (PayloadFile file in state.files)
        {
            string? folder = Path.GetDirectoryName(Within(target, file.path));
            while (folder is not null && folder.StartsWith(target + Path.DirectorySeparatorChar,
                       StringComparison.OrdinalIgnoreCase))
            {
                ownedDirectories.Add(folder);
                folder = Path.GetDirectoryName(folder);
            }
        }
        ownedDirectories.Add(Path.Combine(target, "shortcut-backups"));
        foreach (string folder in ownedDirectories.OrderByDescending(item => item.Length))
        {
            if (!Directory.Exists(folder) ||
                (File.GetAttributes(folder) & FileAttributes.ReparsePoint) != 0 ||
                Directory.EnumerateFileSystemEntries(folder).Any()) continue;
            Directory.Delete(folder);
        }
        bool remaining = Directory.EnumerateFileSystemEntries(target).Any();
        if (!remaining) Directory.Delete(target);
        return (complete, new { status = complete ? "UNINSTALLED" : "PARTIAL_UNINSTALL_RETRY_WITH_SETUP_EXE",
            removed, retained, userDataPreserved = remaining, statePreservedForRetry = !complete, target });
    }

    private static (string[], Dictionary<string, string>) CreateShortcuts(string target, bool consolidate)
    {
        var created = new List<string>();
        var backups = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        var destinations = new[] {
            Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.StartMenu), "Programs", "Morrowind - HALVETH.lnk"),
            Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory), "Morrowind - HALVETH.lnk") };
        for (int i = 0; i < destinations.Length; i++)
        {
            string path = destinations[i];
            if (File.Exists(path))
            {
                if (!consolidate) continue;
                dynamic oldShell = Activator.CreateInstance(Type.GetTypeFromProgID("WScript.Shell")!)!;
                dynamic oldLink = oldShell.CreateShortcut(path);
                string oldTarget = (string)oldLink.TargetPath;
                string expected = Path.Combine(DefaultEngineRoot(), "Morrowind-Workshop.exe");
                // Replace only this project's known earlier Morrowind launcher.
                if (!string.Equals(Path.GetFullPath(oldTarget), expected, StringComparison.OrdinalIgnoreCase))
                    continue;
                string backupDir = Path.Combine(target, "shortcut-backups");
                Directory.CreateDirectory(backupDir);
                string backup = Path.Combine(backupDir, i == 0 ? "start-menu.lnk" : "desktop.lnk");
                File.Copy(path, backup, false);
                backups[path] = backup;
            }
            Directory.CreateDirectory(Path.GetDirectoryName(path)!);
            dynamic shell = Activator.CreateInstance(Type.GetTypeFromProgID("WScript.Shell")!)!;
            dynamic link = shell.CreateShortcut(path);
            link.TargetPath = Path.Combine(target, InstalledExe);
            link.Arguments = "--play";
            link.WorkingDirectory = target;
            link.IconLocation = Path.Combine(target, InstalledExe) + ",0";
            link.Description = "HALVETH Genesis im vorhandenen TES III: Morrowind";
            link.Save();
            created.Add(path);
        }
        return (created.ToArray(), backups);
    }

    private sealed class InstallerForm : Form
    {
        private readonly TextBox target = new() { Width = 520, Text = DefaultTarget() };
        private readonly TextBox engine = new() { Width = 520, Text = DefaultEngineRoot() };
        private readonly TextBox gameData = new() { Width = 520 };
        private readonly Label result = new() { AutoSize = false, Width = 520, Height = 68,
            Text = "Installiert die eigene Genesis-Erweiterung in dein vorhandenes Morrowind. Deine Spielstände und Originaldateien bleiben an ihrem Ort." };
        private readonly CheckBox consolidate = new() { Text = "Vorhandenen HALVETH-Morrowind-Einstieg übernehmen",
            Checked = true, AutoSize = true };

        public InstallerForm()
        {
            Text = Title;
            Width = 610;
            Height = 420;
            StartPosition = FormStartPosition.CenterScreen;
            BackColor = System.Drawing.Color.FromArgb(24, 26, 29);
            ForeColor = System.Drawing.Color.FromArgb(235, 218, 190);
            Font = new System.Drawing.Font("Segoe UI", 10);
            var body = new FlowLayoutPanel { Dock = DockStyle.Fill, FlowDirection = FlowDirection.TopDown,
                WrapContents = false, Padding = new Padding(20), AutoScroll = true };
            var title = new Label { Text = "HALVETH · MORROWIND GENESIS", AutoSize = true,
                Font = new System.Drawing.Font("Georgia", 18, System.Drawing.FontStyle.Bold),
                ForeColor = System.Drawing.Color.FromArgb(232, 166, 126) };
            var button = new Button { Text = "Morrowind einrichten", Width = 230, Height = 40,
                BackColor = System.Drawing.Color.FromArgb(153, 86, 85), ForeColor = System.Drawing.Color.White,
                FlatStyle = FlatStyle.Flat };
            button.Click += (_, _) =>
            {
                button.Enabled = false;
                try
                {
                    var receipt = Install(target.Text, engine.Text, Path.Combine(engine.Text, "profiles", "max"),
                        false, consolidate.Checked, gameData.Text);
                    result.Text = "Installiert. Starte über „Morrowind - HALVETH“.";
                    MessageBox.Show(JsonSerializer.Serialize(receipt, JsonOptions), Title,
                        MessageBoxButtons.OK, MessageBoxIcon.Information);
                }
                catch (Exception ex) { result.Text = ex.Message; button.Enabled = true; }
            };
            body.Controls.Add(title);
            body.Controls.Add(new Label { Text = "Installationsordner", AutoSize = true, Margin = new Padding(0, 18, 0, 2) });
            body.Controls.Add(target);
            body.Controls.Add(new Label { Text = "Vorhandene OpenMW/Morrowind-Quelle", AutoSize = true,
                Margin = new Padding(0, 14, 0, 2) });
            body.Controls.Add(engine);
            body.Controls.Add(new Label { Text = "Eigene Morrowind Data Files (optional bei Voll-Engine)", AutoSize = true,
                Margin = new Padding(0, 14, 0, 2) });
            body.Controls.Add(gameData);
            body.Controls.Add(consolidate);
            body.Controls.Add(button);
            body.Controls.Add(result);
            Controls.Add(body);
        }
    }
}
