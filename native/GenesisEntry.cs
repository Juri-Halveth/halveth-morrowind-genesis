// Native entry into the existing TES III Morrowind/OpenMW installation.
// Compiled alongside the preserved Workshop source; no game assets are embedded.
using System;
using System.Diagnostics;
using System.IO;
using System.Linq;

namespace Halveth.Morrowind {
  public sealed class GenesisEntryConfig {
    public int Schema { get; set; }
    public string Python { get; set; }
    public string Launcher { get; set; }
  }

  public static class GenesisEntry {
    public static GenesisEntryConfig Validate(string root, string profile) {
      if (!new[] {"original", "beauty", "cinematic"}.Contains(profile))
        throw new ArgumentException("Unbekanntes Morrowind-Grafikprofil.");
      string path = Path.Combine(root, "genesis-entry.json");
      if (!File.Exists(path)) throw new FileNotFoundException("Die Morrowind-Startroute fehlt.", path);
      GenesisEntryConfig config = Util.Read<GenesisEntryConfig>(path);
      if (config == null || config.Schema != 1) throw new InvalidDataException("Unbekannte Morrowind-Startroute.");
      ValidateFile(config.Python, "Python-Laufzeit");
      ValidateFile(config.Launcher, "Morrowind-Integration");
      if (!Path.GetFileName(config.Python).Equals("python.exe", StringComparison.OrdinalIgnoreCase))
        throw new InvalidDataException("Die Startroute benötigt die vorhandene python.exe.");
      if (!Path.GetFileName(config.Launcher).Equals("launcher.py", StringComparison.OrdinalIgnoreCase))
        throw new InvalidDataException("Die Startroute benötigt launcher.py.");
      string project = Path.GetDirectoryName(config.Launcher);
      if (!File.Exists(Path.Combine(project, "server.py")) ||
          !File.Exists(Path.Combine(project, "mod", "halveth.omwscripts")))
        throw new InvalidDataException("Die vorhandene Morrowind-Integration ist unvollständig.");
      return config;
    }

    static void ValidateFile(string path, string label) {
      if (String.IsNullOrWhiteSpace(path) || !Path.IsPathRooted(path) || !File.Exists(path))
        throw new FileNotFoundException(label + " wurde am gebundenen lokalen Ort nicht gefunden.");
    }

    public static void Launch(string root, string profile) {
      GenesisEntryConfig config = Validate(root, profile);
      var start = new ProcessStartInfo(config.Python,
        Util.Arg(config.Launcher) + " --play --profile " + Util.Arg(profile)) {
          WorkingDirectory = Path.GetDirectoryName(config.Launcher),
          UseShellExecute = false,
          CreateNoWindow = true,
          RedirectStandardOutput = true,
          RedirectStandardError = true
        };
      using (Process process = Process.Start(start)) {
        if (process == null) throw new IOException("Morrowind konnte nicht gestartet werden.");
        // Drain both streams concurrently so startup diagnostics cannot deadlock.
        var output = process.StandardOutput.ReadToEndAsync();
        var errors = process.StandardError.ReadToEndAsync();
        process.WaitForExit();
        System.Threading.Tasks.Task.WaitAll(output, errors);
        if (process.ExitCode != 0) {
          string detail = errors.Result;
          if (String.IsNullOrWhiteSpace(detail)) detail = output.Result;
          if (detail.Length > 6000) detail = detail.Substring(detail.Length - 6000);
          throw new IOException("Morrowind konnte nicht starten.\n" + detail);
        }
      }
    }
  }
}
