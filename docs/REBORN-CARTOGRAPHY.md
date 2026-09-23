# Reborn-Kartografie: von einem Bild zur sichtbaren Welt

Ein einzelnes Bodentexturbild ist **kein Hash und kein Abbild der gesamten Spielwelt**. Der Quellhash bindet die Bytes der lokalen `Morrowind.esm`; die eigentliche Kartografie entsteht aus `LAND`-Zellen und ihren `LTEX`-Materialindizes. `scripts/cartograph_terrain.py` liest diese Strukturen ohne Änderung der Spieldaten und schreibt den vollständigen lokalen Materialatlas nach `.local/cartography/terrain-atlas.json`. Die Spielinhalte und Zellkarte werden nicht in das öffentliche Quellpaket kopiert.

Der lokale Snapshot vom 23.09.2026 umfasst 1.292 Außen-Landzellen, 330.752 rohe Terrain-Indexpositionen und 100 verwendete Materialindizes der Basis-ESM. Er umfasst weder jedes Objekt, Mesh, Gebäude, NPC, Wetter noch Erweiterungsland. Ein Material zählt, wenn sein Index in einer Zelle vorkommt; das beweist keine konkrete optische Nachbarschaft auf dem Bildschirm.

Die erste sichtbare Materialfamilie heißt **Reborn Bitter Coast**. Sie ersetzt nur vorhandene Texturpfade, keine Quest-, NPC- oder Landschaftsgeometrie:

| Morrowind-Material | Index | Neues eigenes Material | Seyda Neen `(-2,-9)` | `(-2,-10)` |
| --- | ---: | --- | ---: | ---: |
| `Tx_BC_muck` | 92 | Dunkler Torf mit smaragdgrünem Moos | 103 | 26 |
| `Tx_BC_rock_01` | 94 | Verwitterter Küstenfels mit grünen Adern | 105 | 220 |
| `Tx_BC_grass` | 90 | Sattes Marschgras | 28 | 0 |

Im ersten Stand besaßen 236 von 256 rohen Terrain-Indexpositionen der ersten und 246 von 256 der zweiten Seyda-Neen-Landzelle einen der drei neuen Bitterküsten-Materialpfade. Der native Test `python tests/integration_terrain.py` bestätigte inzwischen **alle zehn** eigenen DDS-Dateien im VFS und startete eine Außenzelle ohne Fehler. Der Test `python tests/integration_visuals.py --cell "Seyda Neen" --expect-source weather` bestand für die vorhandene Beleuchtungskette. **Direkte Bildprüfung, Kachelnahtprüfung und FPS unter der finalen Installation fehlen noch**; ein grüner VFS-Test ist kein sichtbarer Vorher/Nachher-Vergleich.

## Reborn World 1.0.4: sieben weitere Materialpfade

Alle sieben PNG-Master sind eigene, mit Codex imagegen aus Textbriefs erzeugte Bodenansichten. Die gleichnamigen DDS-Dateien enthalten dieselben RGB-Pixel im von OpenMW bevorzugten Texturformat. Die Textbriefs und Dateihashes stehen in `ASSET-PROVENANCE.json`; `python scripts/build_reborn_world.py --check` prüft die Formatgleichheit.

| Materialpfad der Basis-ESM | LTEX-Index | Rohe LAND-Positionen | Eigenes Motiv |
| --- | ---: | ---: | --- |
| `tx_ai_dirtroad_01.tga` | 38 | 85.928 | warme Wegerde und kleine Steine |
| `tx_land_darkgravel.tga` | 10 | 25.294 | dunkler Aschekies mit wenigen Mineraltönen |
| `tx_rm_redrock_01.tga` | 16 | 23.863 | rostroter Vulkanfels |
| `tx_rm_rock_02.tga` | 4 | 18.267 | kühler Basaltfels |
| `tx_ac_dirt_01.tga` | 58 | 13.477 | fruchtbare Erde mit grünem Moos |
| `tx_rm_grayrock_01.tga` | 15 | 12.494 | grauer Schieferfels |
| `tx_ma_crackedearth.tga` | 66 | 8.757 | trockene, rissige Erde |

Mit den drei Bitterküsten-Pfaden betreffen die zehn ausgewählten Materialnamen 217.256 von 330.752 rohen Terrain-Indexpositionen (65,7 %) in 1.292 Außen-Landzellen des untersuchten lokalen `Morrowind.esm`-Snapshots. Das bedeutet **nicht**, dass 65,7 % der sichtbaren Welt neu gestaltet wären: Positionen sind weder Flächenmaß noch Sichtbarkeits- oder Qualitätsmessung. Die neuen Farben können an Übergängen zu älteren Materialien auffallen; tatsächliche Kachelnaht, Lichtwirkung, Außenzellenbild und FPS müssen im finalen Spiel verglichen werden. Gebäude, Vegetationsmodelle, NPCs und Innenräume bleiben von diesen sieben Bodentexturen unverändert.

Die weitere Weltgestaltung folgt demselben Ingame-Pfad: Region und Materialfamilie aus dem lokalen Atlas wählen, benachbarte Materialwerte gemeinsam entwerfen, eigene Assets in den OpenMW-Datenpfad legen, VFS und Szene testen, dann am gleichen Kamerastand bei gleichem Wetter vor/nach vergleichen. Für Gebäude, Körper und Animationen sind eigene Modelle und separate Ingame-Tests nötig. Die alten Morrowind-Aufgaben und Spielstände bleiben dabei erhalten.
