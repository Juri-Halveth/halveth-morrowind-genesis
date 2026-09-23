# Reborn-Kartografie: von einem Bild zur sichtbaren Welt

Ein einzelnes Bodentexturbild ist **kein Hash und kein Abbild der gesamten Spielwelt**. Der Quellhash bindet die Bytes der lokalen `Morrowind.esm`; die eigentliche Kartografie entsteht aus `LAND`-Zellen und ihren `LTEX`-Materialindizes. `scripts/cartograph_terrain.py` liest diese Strukturen ohne Änderung der Spieldaten und schreibt den vollständigen lokalen Materialatlas nach `.local/cartography/terrain-atlas.json`. Die Spielinhalte und Zellkarte werden nicht in das öffentliche Quellpaket kopiert.

Der lokale Snapshot vom 23.09.2026 umfasst 1.292 Außen-Landzellen, 330.752 rohe Terrain-Indexpositionen und 100 verwendete Materialindizes der Basis-ESM. Er umfasst weder jedes Objekt, Mesh, Gebäude, NPC, Wetter noch Erweiterungsland. Ein Material zählt, wenn sein Index in einer Zelle vorkommt; das beweist keine konkrete optische Nachbarschaft auf dem Bildschirm.

Die erste sichtbare Materialfamilie heißt **Reborn Bitter Coast**. Sie ersetzt nur vorhandene Texturpfade, keine Quest-, NPC- oder Landschaftsgeometrie:

| Morrowind-Material | Index | Neues eigenes Material | Seyda Neen `(-2,-9)` | `(-2,-10)` |
| --- | ---: | --- | ---: | ---: |
| `Tx_BC_muck` | 92 | Dunkler Torf mit smaragdgrünem Moos | 103 | 26 |
| `Tx_BC_rock_01` | 94 | Verwitterter Küstenfels mit grünen Adern | 105 | 220 |
| `Tx_BC_grass` | 90 | Sattes Marschgras | 28 | 0 |

Damit besitzen 236 von 256 rohen Terrain-Indexpositionen der ersten und 246 von 256 der zweiten Seyda-Neen-Landzelle einen der drei neuen Materialpfade. Die übrigen Materialien und die gesamte Welt jenseits dieser Flächen bleiben offen. Der native Test `python tests/integration_terrain.py` bestätigte, dass OpenMW alle drei eigenen DDS-Dateien im VFS auswählt und eine Außenzelle ohne Fehler startet. Der Test `python tests/integration_visuals.py --cell "Seyda Neen" --expect-source weather` bestand ebenfalls. **Direkte Bildprüfung, Kachelnahtprüfung und FPS unter der finalen Installation fehlen noch**; ein grüner VFS-Test ist kein sichtbarer Vorher/Nachher-Vergleich.

Die weitere Weltgestaltung folgt demselben Ingame-Pfad: Region und Materialfamilie aus dem lokalen Atlas wählen, benachbarte Materialwerte gemeinsam entwerfen, eigene Assets in den OpenMW-Datenpfad legen, VFS und Szene testen, dann am gleichen Kamerastand bei gleichem Wetter vor/nach vergleichen. Für Gebäude, Körper und Animationen sind eigene Modelle und separate Ingame-Tests nötig. Die alten Morrowind-Aufgaben und Spielstände bleiben dabei erhalten.
