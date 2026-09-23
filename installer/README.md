# Windows-Einzeldatei-Installation

`installer/build_installer.py` baut eine **einzige Setup-EXE**. Ein Klick installiert den nativen HALVETH-Einstieg, die eigene OpenMW-Mod, Bücher, Zauber, UI und den lokalen Gesprächsbegleiter. Die Python-3.14.7-Laufzeit steckt geprüft in der EXE. Nach der Installation ist `HALVETH Morrowind.exe` der sichtbare Spieleinstieg; es startet das echte OpenMW/Morrowind und seinen Begleiter.

Die öffentliche Variante `HALVETH-Morrowind-Genesis-1.0.3-Setup.exe` benötigt eine vorhandene, konfigurierte OpenMW-0.51.0-Installation im HALVETH-Layout (`engine/openmw.exe`, `profiles/max/openmw.cfg`, `profiles/max/settings.cfg`). Die nur lokal erzeugbare Variante `HALVETH-Morrowind-Genesis-1.0.3-Local-Engine-Setup.exe` enthält zusätzlich die vorhandene OpenMW-Engine, deren Standardressourcen und GPLv3-Lizenz. Sie kann entweder ein bestehendes Profil samt Mod-Ladereihenfolge übernehmen oder mit `--game-data` nur den eigenen lizenzierten `Data Files`-Ordner anbinden. Sie wird **nicht veröffentlicht**, bevor die genauen Binärdateien, Abhängigkeiten und die zugehörige Quellbereitstellung vollständig geprüft sind. Beide Varianten nutzen die Morrowind-Daten aus der eigenen lizenzierten Installation; sie kopieren oder verbreiten weder `Morrowind.esm`, Erweiterungen, Spielstände, heruntergeladene Grafikpakete noch Modellgewichte.

```powershell
python installer/build_installer.py
python installer/build_installer.py --local-engine --engine-directory "<OpenMW-0.51.0-engine-Ordner>"
```

Der Builder lädt nur zur **Buildzeit** das offizielle Python-Einbettungspaket von python.org. Sein SHA-256 muss mit dem Wert auf der [Python-3.14.7-Release-Seite](https://www.python.org/downloads/release/python-3147/) übereinstimmen. `runtime/LICENSE.txt` wird mit installiert. Das lokale OpenMW-Paket stammt aus dem eigenen bereits installierten Engine-Ordner; [Version und Quelle 0.51.0](https://gitlab.com/OpenMW/openmw/-/tags/openmw-0.51.0), GPLv3-Lizenz und Ressourcen bleiben im installierten `engine/`-Ordner. Die private Voll-Engine-Variante nimmt ausschließlich die Pfade im überprüfbaren [OpenMW-Runtime-Inventar](openmw-0.51.0-runtime-files.txt) auf; neu hinzugekommene Logs, Dumps, Spielstände oder andere Dateien aus diesem lokalen Ordner gelangen nicht in die EXE. Keine externe Datenabfrage ist während der Installation nötig.

Das Installer-Symbol entsteht zur Buildzeit aus `installer/love-astrolabe-icon-0.8.png`. Dieses quadratische Originalmotiv wurde mit Codex imagegen aus dem bereits eigenen LOVE-Astrolabium als Stilreferenz erzeugt. Die ICO-Datei ist nur ein Formatderivat für Windows; Lizenz und Hash des PNG gehören in `ASSET-PROVENANCE.json`.

Der Installer prüft jede Nutzdatei gegen sein eingebettetes SHA-256-Manifest und installiert zuerst in ein frisches Staging-Verzeichnis. Ein bereits belegtes Ziel wird nicht überschrieben. Das Quellprofil wird nur gelesen. In der lokalen Voll-Engine-Variante wird eine eigene Profilkopie mit absoluten Pfaden auf vorhandene, eigene Spieldaten geschrieben. `--no-shortcuts` erzeugt keine Verknüpfung. `--consolidate-shortcuts` ersetzt ausschließlich die bekannten älteren Desktop-/Startmenü-Links `Morrowind - HALVETH`, falls diese exakt auf den früheren `Morrowind-Workshop.exe`-Einstieg zeigen; Sicherungskopien liegen im neuen Installationsordner und werden beim regulären Deinstallieren zurückgesetzt. Andere Verknüpfungen bleiben unverändert.

```powershell
& "<Setup-EXE>" --install --target "<neuer Zielordner>" --engine-root "<vorhandene HALVETH-OpenMW-Installation>" --source-profile "<vorhandenes OpenMW-Profil>" --no-shortcuts
& "<Setup-EXE>" --check --target "<Zielordner>"
& "<Setup-EXE>" --uninstall --target "<Zielordner>"
```

Mit dem lokalen Voll-Engine-Paket ist auch diese frische Installation ohne vorhandenes OpenMW-Profil möglich:

```powershell
& "<Local-Engine-Setup-EXE>" --install --target "<neuer Zielordner>" --game-data "<eigener Morrowind/Data Files-Ordner>" --no-shortcuts
```

Für die bestehende Eintragsumstellung statt `--no-shortcuts` `--consolidate-shortcuts` nutzen. Das normale Setup-Fenster bietet dieselbe gezielte Option. Änderungen an installierten Dateien bleiben bei der Deinstallation erhalten; persönliche `.local`-Profile, Spielstände und Gesprächsdateien werden nicht gelöscht. Eine im Moment der Deinstallation laufende installierte EXE kann Windows erst nach dem Beenden freigeben; dann bleibt `install-state.json` für einen späteren erneuten Rückbau erhalten und der Befehl meldet einen Teilrückbau mit Fehlercode. Hierfür die ursprüngliche Setup-EXE nach Beenden des Spiels erneut verwenden.

**Technische Grenze:** „eine Setup-EXE“ und „ein sichtbarer Spieleinstieg“ sind umgesetzt. Die laufende Engine, eigene Lua-Skripte, Python-Begleiter und die lizenzierten Morrowind-Spieldaten sind nach dem Installieren weiterhin getrennte Dateien und Prozesse. Ein vollständiges Morrowind mit Bethesda-Inhalten lässt sich nicht redlich oder rechtmäßig als freie einzige EXE ausliefern. Das lokale Modell für freie NPC-Gespräche bleibt ein optionaler, bereits installierter Ollama-Dienst; die nativen Spielansichten und Werkzeuge funktionieren auch ohne ihn.
