# Grafik in Genesis 0.2

**Scarlet Beauty** ist das Standardprofil für 2560 × 1440 auf der vorhandenen RTX 4070 SUPER. Die lokale Installation enthält jetzt neue Gesichter und Frisuren, 162 Landschaftstexturen in 2K, einen 8K-Sternenhimmel sowie Kontaktschatten, Wolken, dezentes Bloom und HDR-Tonemapping. Der vollständige Beauty-HD-Aufbau wurde in einer frischen Seyda-Neen-Szene erfolgreich gestartet.

## Tatsächlich installiert

Der lokale Stand ist in `.local/graphics/install.json` gebunden. Zum Dokumentstand 19.09.2026 sind diese **sieben Pakete installiert**:

| Paket | Gebundener Quellstand | Verwendete Wirkung |
| --- | --- | --- |
| [Zesterer SSAO](https://github.com/zesterer/openmw-ssao/tree/fa5ec4303ee557b75e3c51c02ab14ff0334271c4) | `fa5ec4303ee5` | Kontaktschatten und räumliche Tiefe |
| [Zesterer Volumetric Clouds](https://github.com/zesterer/openmw-volumetric-clouds/tree/c8830bcd2de0f6e7355f91880308426203eded3c) | `c8830bcd2de0` | Wetterabhängige Wolken und Nebel |
| [Wareya OpenMW Shaders](https://github.com/wareya/OpenMW-Shaders/tree/76e0637187cc2878575528119aed72bbbf1a12cf) | `76e0637187cc` | HDR-Tonemapping und FollowerAA-Kantenglättung |
| [Tyddy Landscape Retexture HQ](https://www.fullrest.ru/files/tyd_landscape-texture_compilation_1) | `1.0` | 162 aktive Landschaftstexturen in 2K |
| [Khajiit Head Pack](https://gitlab.com/portmod/openmw-mods/-/tree/master/npcs-bodies/khajiit-head-pack) | `1.4` | Neue Khajiit-Köpfe |
| [Sophie / Dying Moons Starfield](https://modding-openmw.gitlab.io/sophies-skooma-sweetshoppe/) | `2.0.2.5` | 8K-Sternenhimmel |
| [Better Heads](https://www.nexusmods.com/morrowind/mods/42226) | `2.0` laut eingebetteter Readme | Neue Gesichter und Frisuren |

Bloom stammt aus der installierten OpenMW-Engine. Die konfigurierte Reihenfolge lautet:

```text
ssao → clouds → bloomlinear → hdr_linear → FollowerAA
```

HDR bezeichnet hier die Bildnachbearbeitung des Spiels; daraus folgt keine aktivierte HDR-Ausgabe des Monitors. Weitere im Wareya-Paket mitgelieferte Effekte sind durch diese Kette nicht automatisch aktiv.

Der eigene Adapter `HALVETH-Beautiful-Heads.esp` verbindet die Kopfpakete mit **302 vorhandenen Modellzuordnungen**. Er ändert ausschließlich `BODY.MODL`: **0 NPC-, Quest- oder Inventardatensätze**, keine gelöschten Records. Die bisherigen Plugins bleiben in ihrer Reihenfolge; anschließend kommen der geprüfte Darstellungsadapter und der Genesis-Lua-Mod. Die Original-ESMs der Kopfpakete werden nicht aktiviert. Der lokale Nachweis liegt in `.local/graphics/mods/genesis-head-adapter/adapter-receipt.json`.

Bei `clouds` ist **Replace Skybox ausgeschaltet** (`replace_skybox = false`), damit Sophies installierter Sternenhimmel erhalten bleibt. Diese Einstellung beim eigenen Abstimmen beibehalten, wenn die neuen Sterne sichtbar bleiben sollen.

## Spielen und einstellen

Im Genesis-Launcher **Scarlet Beauty** wählen. **Grafikvorlage anwenden** übernimmt die aktuellen Empfehlungen mit Sicherung. Danach **Genesis spielen** starten. Ein normaler Start erhält bereits gespeicherte persönliche Grafikeinstellungen.

Alternativ aus dem Projektordner:

```powershell
python scripts/prepare_profile.py --profile beauty --reset-settings
python scripts/prepare_profile.py --profile beauty --launch
```

Im Spiel öffnet **F2** die Shaderverwaltung. Dort lassen sich die aktiven Effekte und ihre Regler einstellen. Für einen eigenen Vergleich zuerst bei gleicher Szene und gleichem Wetter bleiben und einen Regler nach dem anderen ändern:

- Zu dunkle Ecken: bei `ssao` **Intensity** reduzieren. Beauty startet mit `6.0` und 30 Samples.
- Zu viel Nebel: bei `clouds` **Mist → Density** reduzieren; Beauty startet mit `0.12`, Cinematic mit `0.18`. **Interior Mist** steht auf `0.025`.
- Zu starker Lichtschein: bei `bloomlinear` **Strength** reduzieren; Beauty startet mit `0.08`, Cinematic mit `0.12`.
- Zu starke Aufhellung: bei `hdr_linear` **Maximum exposure** reduzieren; die Vorgabe ist `1.25`.
- Für mehr Leistung zuerst die **Sampling Quality** der Wolken oder die **Max Samples** von SSAO senken.

FollowerAA steht am Ende der Kette. Bei dieser Kombination ist MSAA ausgeschaltet. Der ferne Engine-Nebel ist ebenfalls ausgeschaltet, weil der Wolkenshader seine eigene Atmosphäre berechnet. Diese Kombination folgt den [Empfehlungen des Wolkenpakets](https://github.com/zesterer/openmw-volumetric-clouds/tree/c8830bcd2de0f6e7355f91880308426203eded3c#recommendations).

## Profile

| Profil | Sichtweite | Schatten | Wasser-Renderziel | Zweck |
| --- | ---: | --- | ---: | --- |
| Original | Aus dem bisherigen Ausgangsprofil | Aus dem Ausgangsprofil | Aus dem Ausgangsprofil | Vergleich mit der bisherigen Darstellung; ohne zusätzliche Manifestpakete |
| Scarlet Beauty | 81.920 | 3 Karten à 4.096; Distanz 16.384 | 2.048 | Standard zum Spielen |
| Cinematic | 131.072 | 3 Karten à 8.192; Distanz 24.576 | 4.096 | Aufwendigere Panoramen und eigene Bildvergleiche |

Sicht- und Schattendistanzen sind OpenMW-Einheiten. Beide neuen Grafikvorlagen verwenden 16-fache Texturfilterung, Shader-Beleuchtung, automatisch erkannte Normalmaps und weiche Partikel. Cinematic erhöht zusätzlich Terrain-Details, SSAO-Samples auf 48 und Wolken-Samplingqualität auf `1.5`. Das benötigt mehr GPU-Leistung und Speicher; auch die lokale KI beansprucht die GPU. Der Beauty-Prüfstand steht unten; Zusätzlich bestanden die Innenraumszene mit Arrille und Cinematic bei Nacht; echte Screenshots wurden gespeichert.

## Sicherung und Rückkehr

Profile liegen in `.local/profiles/<profil>/`. `--reset-settings` beziehungsweise **Grafikvorlage anwenden** sichern vorhandene Dateien als `settings.cfg.<UTC-Zeit>.bak` und `shaders.yaml.<UTC-Zeit>.bak`, bevor die neuen Vorgaben geschrieben werden. Die Sicherungen werden durch Hashvergleich geprüft. Spiel-, Ton-, Eingabe- und Fensterpräferenzen werden beim Übernehmen der Grafikwerte erhalten; ein erneutes Anwenden setzt die Shaderregler auf die jeweilige Vorlage zurück.

Für die Rückkehr das Spiel schließen und die gewünschte Sicherung im gleichen Profil auf ihren ursprünglichen Namen zurückkopieren. Die zuvor bestehende Installation und ihre Spielstände bleiben erhalten. Die zusätzlichen Grafikverzeichnisse folgen nach den ursprünglichen Spieldaten; der geprüfte BODY-Adapter ergänzt die vorhandene Content-Liste, deren bisherige Einträge und Reihenfolge unverändert bleiben.

## Lokale Pakete und Quellcode-Ausgabe

Die drei gebundenen Shaderpakete lassen sich aus dem Quellpaket erneut lokal installieren. Dieser Befehl installiert ausschließlich diese Shader; Köpfe, Landschaft und Sterne sind getrennte lokale Assets:

```powershell
python scripts/install_shaders.py
python scripts/prepare_profile.py --profile beauty --reset-settings
```

Der Installer lädt ausschließlich die oben genannten festen Quellstände und prüft ihre eingebundenen SHA-256-Werte. Pro Archiv gelten 32 MiB Download- und 64 MiB Entpackgrenze. Bereits vorhandene passende Archive werden wiederverwendet; bestehende Paketdateien werden mit dem geprüften Archiv verglichen. Bei Abweichungen stoppt der Installer und lässt das vorhandene Paketverzeichnis unverändert. Er führt keinen heruntergeladenen Programmcode aus und startet das Spiel nicht. Andere eingetragene Grafikpakete und ihre Metadaten bleiben erhalten; die drei Shaderverzeichnisse werden vor den bisherigen Texturverzeichnissen eingeordnet. Ein vorhandenes Installationsmanifest wird vor der Zusammenführung gesichert. Der Installer selbst ist im Quellpaket enthalten, die heruntergeladenen Inhalte sind es nicht.

Der Profilhelfer liest zuerst `<Zustandsordner>/graphics/install.json`, anschließend `.local/graphics/install.json` und zuletzt `data/graphics-install.json`. `--graphics-manifest` wählt eine eigene Datei. Sie bindet Datenverzeichnisse und Shaderreihenfolge. `visualPlugins` werden nur mit passendem Hash und vollständiger Prüfung auf TES3-Header plus `BODY`-Records eingebunden; Quest-, Dialog- und NPC-Records sind dort nicht zulässig.

**Das Source-ZIP enthält keine fremden Grafikassets.** Shaderpakete, Texturen, Modelle, der lokal abgeleitete Kopfadapter, persönliche Profile, Spielstände, Datenbanken, Logs und Screenshots bleiben außerhalb des Archivs. Enthalten sind unsere Helfer, der Shaderinstaller und die Dokumentation. Die Rechte der jeweiligen Autoren bleiben bei ihren Paketen; das Quellarchiv lizenziert deren Inhalte nicht neu. Ohne lokales Grafikmanifest verwendet ein frisches Beauty-Profil den eingebauten Bloom-Shader.

## Prüfstand und technische Grundlage

**Beauty HD: nativer Test bestanden.** In der frischen Seyda-Neen-Szene bei 2560 × 1440 meldete der Lauf Exit-Code `0` und keine protokollierten Fehler. Nach dem Aufwärmen wurden über 25,025 Sekunden 1.113 Frame-Callbacks gemessen, entsprechend **44,48 FPS im Mittel**. Das ist eine kurze Szenenmessung, kein Dauerlast- oder GPU-Benchmark und kein allgemeines FPS-Versprechen. Es wurde kein bestehender Spielstand geladen. Quelle: `.local/graphics/checks/beauty-hd-final/result.json`.

Auch die Innenraumszene mit Arrille sowie Cinematic bei 23 Uhr bestanden bei 2560 × 1440 mit Exit-Code 0 und ohne protokollierte Fehler. Der neue Sternenhimmel, die Köpfe und die Tageslandschaft wurden direkt im Spiel angesehen und als Screenshots gespeichert. Eine frische Vivec-Sitzung bestätigte anschließend +250 Gold, die Erkennung einer wiederholten Aktions-ID, vollständige Heilung sowie Öffnen/Schließen der JARVIS-Oberfläche. Elf Python-Tests bestanden. Details stehen in `GRAPHICS-RESULT.json`. Der automatisierte F8-/F12-Tastendruck blieb ohne sichtbare Wirkung; der Fensteraufbau wurde zusätzlich über die exportierte Mod-Schnittstelle geprüft. Der Vergleich `key.code == input.KEY.F8` entspricht der installierten OpenMW-0.51-API.

Die Profilwerte sind gegen die [OpenMW-0.51-Einstellungsschlüssel](https://github.com/OpenMW/openmw/blob/openmw-0.51.0/files/settings-default.cfg) und die installierten Shaderdefinitionen geprüft. Dateierhalt, Sicherungen und Erhalt der bisherigen Content-Reihenfolge wurden mit getrennten Testprofilen geprüft.

OpenMW lädt die Regler aus `shaders.yaml` über seinen [ShaderManager](https://github.com/OpenMW/openmw/blob/openmw-0.51.0/components/settings/shadermanager.hpp); Genesis schreibt dafür gültiges JSON im YAML-Format. Die [offizielle Postprocessing-Dokumentation](https://openmw.readthedocs.io/en/openmw-0.51.0/reference/modding/settings/postprocessing.html) beschreibt `enabled`, die geordnete `chain` und den F2-Dialog. Ein gesetzter Shadername allein ist noch keine erfolgreiche native Kompilierung.
