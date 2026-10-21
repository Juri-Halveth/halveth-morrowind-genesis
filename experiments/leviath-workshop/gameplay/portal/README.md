# LEVIATH-Seelenstein: lokaler Portal-Kandidat 0.1.2

Eigene OpenMW-0.51/API129-Lua-Einheit mit zwei neuen Activator-Referenzen.
Der erste Stein liegt bei Seyda Neen, der zweite auf der neuen eigenen
Frontier-Flaeche. Die Portalregistration enthaelt weder Courier-Fixtures noch
eine automatisch erzeugte Geschenksendung.

Der Planer liest den wirklichen Frontier-`ENTRY.json`, prueft dessen Digest
und den ESP-Digest und leitet die Zielkonfiguration daraus ab. Das gebundene
Ziel ist `LEVIATH Frontier Entry`, Exterior-Grid `(65,-63)`, Ausgangspunkt
`(536576,-512000,576)`. Die 256 Einheiten Hoehenreserve ueber der dekodierten
Landflaeche wurden bei der nativen Spielerlandung beobachtet. Der stationaere
Stein verwendet separat die gebundene Terrainhoehe 320; er erhaelt keine
fuer den ankommenden Spieler bestimmte Hoehenreserve.

Der Spieler aktiviert den Stein mit seiner normalen Spielaktion. Ein nativer
Reiseprompt erlaubt Reisen oder Schliessen. Nur die anschliessende Bestaetigung
des bei diesem Stein stehenden Spielers loest genau eine Engine-Reise aus.
Der vorherige Standort und seine Blickrichtung bleiben als Rueckkehrpunkt im
eigenen Save. Ein Reload stellt Referenzen und Zustand wieder her und loest
keine neue Teleportation aus. Fehlende Referenzen oder ein unklarer Abschluss
bleiben als HOLD erhalten; es werden keine Ersatzsteine erzeugt.

Die Gem-Geometrie wird als vorhandene lokale Morrowind-Modellreferenz verwendet.
Kein Original-CELL-Record und keine Originalreferenz wird ersetzt. `mod/`
enthaelt nur eigenen MIT-Code. Originalmodelle, Texturen, ESM/BSA und Spiel-
staende gehoeren nicht in ein oeffentliches Quellpaket.

```bash
/c/Python314/python.exe prepare_portal.py
/c/Python314/python.exe bind_model.py
/c/Python314/python.exe validate_portal.py
bash PORTAL_BASH.sh stage
bash PORTAL_BASH.sh probe
bash PORTAL_BASH.sh reload-frontier
bash PORTAL_BASH.sh reload-returned
bash PORTAL_BASH.sh play
```

Zusaetzliche Mod-Daten/Content-Zeilen fuer ein eigenes Profil:

```ini
data="<eigener Frontier-Kandidat>/mod"
data="<eigener Portal-Kandidat>/mod"
content=LEVIATH-Frontier.esp
content=veyra-portal.omwscripts
```

`play` beginnt im normalen Engine-Menue. Ein automatischer Start benoetigt
`play --save "<vorhandener eigener Portal-Save.omwsave>"`. Das Profil waehlt
keinen Debug-Save ungefragt aus. Beim expliziten Laden eines Verifikations-
saves bleibt dessen benoetigte Probe-Registration kompatibel, ihre OnLoad-
Handler stoppen jedoch Positionierungs-/Kontroll-Fixtures.

Am 03.10.2026 liefen mit demselben 0.1.2-Produktionscode drei native Pruefungen:

- Hin- und Rueckreise: 17 PASS, Exit 0. Zwei eigene Activators, Distanzsperre,
  echte `activateBy(player)`-Engine-Ereignisse, sichtbare normale Reiseprompts,
  realer Frontier-Aufenthalt, Landung, exakter Rueckkehrpunkt und Blickrichtung,
  erhaltene Ref-IDs sowie erneute Bestaetigung ohne weitere Reise.
- Save auf der Frontier: 5 PASS, Exit 0. Gleiche zwei Ref-IDs und Rueckkehrpunkt
  wieder geladen; das Laden bewegte den Spieler nicht und zaehlte keine Reise.
- Save nach Rueckkehr: 5 PASS, Exit 0. Derselbe Referenz-/Trip-/Rueckweg-Befund
  auf der Ausgangsseite.

Jeder Durchlauf band 14 Originaldateien vor und nach dem Lauf; ihre Digests
blieben unveraendert. Receipts liegen in `evidence/*-RECEIPT.json`; der vier-
Dateien-Produktionsfreeze und seine dazu passenden nativen Receipts sind in
`FREEZE_PORTAL.json` gebunden. `evidence/probe-window-2.png` zeigt den nativ
gerenderten Hinreise-Prompt, `probe-window-3.png` den Rueckweg-Prompt. Sie sind
lokale QA-Bilder vorhandener Spielassets und bleiben ausserhalb des Quellpakets.

Die eingebettete `entryBinding` bewahrt den damaligen Planerstand mit
`NOT_RUN` / `PENDING_ROOT_PROBE`. Die spaeteren nativen Beobachtungen sind
separat in `nativeResults` und den gebundenen Receipts gefuehrt.

Die zwei ersten fehlgeschlagenen Entwicklungslaeufe bleiben in den History-
Receipts erhalten: ein MWUI-Templatefehler und die unpassende Hoehenreserve
eines statischen Ruecksteins. Der bestandene Pruefstand verwendet echte
Engine-Aktivierung und die normale Spieler-UI; ein physischer Tastendruck zur
Aktivierung wurde nicht unabhaengig getestet. Die optionale neue Plaza ist in
diesen eigenen Proben nicht geladen. Mehrere Spieler, Gaeste oder andere
Weltserver werden durch dieses lokale Modul nicht angebunden.

Primaerquellen: [OpenMW world](https://openmw.readthedocs.io/en/openmw-0.51.0/reference/lua-scripting/openmw_world.html),
[core: activateBy/teleport/setScale](https://openmw.readthedocs.io/en/openmw-0.51.0/reference/lua-scripting/openmw_core.html),
[types: Activator- und Miscellaneous-Records](https://openmw.readthedocs.io/en/openmw-0.51.0/reference/lua-scripting/openmw_types.html)
und die konkreten `resources/lua_api/openmw/` Dateien der vorhandenen Engine.
