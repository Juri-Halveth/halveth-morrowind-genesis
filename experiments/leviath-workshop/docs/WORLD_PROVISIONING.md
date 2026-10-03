# Eigene Weltkopien mit Git Bash

`scripts/provision-world.sh` ist der neue Installer. Er plant und kopiert das eigene Workshop-Paket in einen neuen Zielordner; `scripts/workshop.sh` startet danach die ausdrücklich gewählte externe OpenMW-Engine mit diesem neuen Profil. `scripts/provision.sh` und seine historischen nativen Receipts bleiben als0.1.2-Referenz erhalten.

Die Engine, ihre Ressourcen und deine vorhandenen Morrowind-Daten werden als vorhandene lokale Quellen gebunden. Das neue Profil bekommt eigene `user-data`- und `data-local`-Ordner. Optional vorhandene `shaders.yaml` und `input_v3.xml` werden als getrennte Dateien kopiert. Wiederholte `data`, `content` und `fallback`-Einträge behalten ihre Reihenfolge. Vorhandene Spielstände, globale Lua-Speicher, Logs und Navmesh-Caches werden nicht automatisch übernommen.

```bash
export WORKSHOP_PYTHON=python
bash scripts/provision-world.sh plan \
  --base-profile '/c/Games/MyOpenMW/profile' \
  --engine '/c/Games/OpenMW/openmw.exe' \
  --destination '/c/Games/Leviath-Workshop-02' \
  --modules 'scenery,plaza,courier,hud,fieldwork,portal,construction,townlife,audio'
```

Der Plan enthält die angefragten und tatsächlich benötigten Module sowie alle Eingabe- und Kopierhashes. Die Pfade und der Plan sind lokal vertraulich. Für die Anwendung dieselben Argumente mit `apply` verwenden; `--expect-plan DIGEST` kann den zuvor geprüften Plan exakt binden. Das Ziel muss neu sein. Der Installer lädt keine Pakete herunter und führt keine Engine aus.

| Gewähltes Modul | Automatisch gebundene Abhängigkeiten |
| --- | --- |
| `frontier` | Eigener additiver Welt-ESP und drei eigene DDS |
| `frontier-textures` | `frontier`; drei ausdrücklich ausgewählte eigene DDS-Überlagerungen |
| `plaza` | `frontier`, `frontier-textures`; eigene Platz-Geometrie und eigener additiver ESP |
| `bark` | Zwei exakt gebundene Poly-Haven-CC0-Materialdateien mit vollständiger Lizenz und Quellenbindung |
| `crown` | `bark`; eigene Baumgeometrie, Blatttextur und additiver ESP |
| `scenery` | `frontier`, `frontier-textures`, `crown`;68 eigene Baum-, Stein- und Grasreferenzen |
| `portal` | `frontier`, `panels`; registrierte eigene Hin- und Rückreise |
| `construction` | `frontier`, `panels`; eigenes Beetmodell und bestehende Bauquellen |
| `townlife` | `frontier`, `frontier-textures`, `plaza`; drei eigene Bürger und eigenes Statuspanel |
| `courier`, `fieldwork` | `panels`; ihre ursprünglichen Registrierungen bleiben jeweils einmal aktiv |
| `hud` | Eigenes HUD0.1.4 mit lokal erzeugtem PNG |
| `audio` | `courier`; exakt gebundener130.630-Byte-CC0-Monoton samt ursprünglicher Kenney-Lizenz und Buildreceipt |

`panels` ist ein exakt gebundener14-Dateien-Overlay: Coordinator, Courier0.2.4 sowie neun Spielerfenster-Hooks. Er liegt nach den gebundenen eigenen Basismodulen im VFS. Bestehende eigene Genesis-Registrierungen und weitere Genesis-Globals bleiben Abhängigkeiten des gewählten Basisprofils; die sechs vorhandenen eigenen Genesis-Spielerfenster werden nur bei dieser Registrierung ausgeführt. Der Installer installiert keine vollständige Genesis-Basis aus diesen sechs Hookdateien.

Andere vorhandene Versionen derselben VFS-Pfade werden abgewiesen. Der bekannte Originalstand und der exakt gebundene neue Hookstand sind ausdrücklich zulässige Varianten. Die eigenen Frontier-Texturen dürfen nur die ebenfalls gebundenen eigenen Frontier-Texturstände überlagern. Alle geschriebenen Dateien sind neue Kopien; Engine-Hardlinks erhalten keine Schreiboperation.

```bash
bash scripts/workshop.sh play \
  --engine '/c/Games/OpenMW/openmw.exe' \
  --profile '/c/Games/Leviath-Workshop-02/profile'
```

Das öffnet das normale Menü. Einen vorhandenen Save nur ausdrücklich mit `--save PATH` wählen. Die gewöhnliche Spielroute aktiviert keine Probe, gibt keine Testgegenstände und teleportiert den Spieler nicht. Die neuen eigenen Gebiete beginnen weit außerhalb der bisherigen Welt; das Portal ist die eigene Reiseroute.

Ein Seelenstein wird mit der bestehenden Aktion **Aktivieren** angesprochen. Die vorhandene Profilbelegung bleibt erhalten. Der neue Courier trägt die Zuordnung **K**. Native UI-Interfaces, Reisebestätigung und Depot-Claim wurden tatsächlich geprüft; der getrennte OS-Key-Snapshot beobachtete null Lua-KeyPress/KeyRelease-Events. Physische Tastatur- und Mausbedienung bleibt eine eigene offene Prüfkante. Die normalen leeren Spielstände bleiben ohne synthetische Sendung.

Das Paket liefert eigene MIT-Quellen und ausdrücklich gebundene eigene Verfahrensassets. Zwei Bark-DDS und der Kenney-Monoton behalten ihre eigene CC0-Lizenz. [Poly Haven](https://polyhaven.com/license) erlaubt die Weitergabe seiner CC0-Assets; [Kenney Impact Sounds](https://kenney.nl/assets/impact-sounds) weist das ausgewählte Paket ebenfalls als CC0 aus. Vollständige Lizenztexte und die Quellen-/Transformationshashes liegen im Paket. OpenMW und Morrowind werden getrennt bereitgestellt und behalten ihre jeweiligen Rechte.

`prototypes/wildlife-source-only` enthält getrennte eigene Generator-/Lua-Quellen des deaktivierten Felsenhirsch-Prototyps. Dieses Verzeichnis ist kein Installer-Modul, wird nicht automatisch registriert und liefert keine fertigen Modelle. Seine vorhandenen nativen Einzelbeobachtungen gehören ausschließlich zum getrennten Prototypstand. Musik und Atmosphärendateien sind im aktuellen Schnitt nicht ausgewählt.

Die vorbereiteten exakten Weltassets lassen sich direkt installieren. Die eingefrorenen historischen Generatoren bleiben als eigene überprüfbare Quellen enthalten; ihre lokalen Kollisions-/Rebuild-Bindings werden als Eingabeparameter benötigt. Private Profilreceipts, Debug-Fixtures und Originaldaten werden dafür nicht mitverteilt. Ein allgemeiner Neubau der ganzen Welt mit einem beliebigen Basisprofil wird deshalb nicht als fertiger Ein-Befehl-Weg behauptet. Ein solcher Neubau muss neue lokale Inhalts-/Kollisionsbindungen erzeugen und erhält danach seine eigene Prüfung.
