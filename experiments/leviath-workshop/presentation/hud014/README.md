# Veyra HUD 0.1.4 – lesbare Ortsnamen

Eigene getrennte Datenüberlagerung des eingefrorenen HUD0.1.3. Der vorherige HUD-Fallback verwendete `cell.region` unmittelbar als Text. Das ist eine Regions-ID; die eigene Frontier enthält bereits den Anzeigenamen `LEVIATH Frontier` im FNAM. Diese Version liest den vorhandenen Engine-Anzeigenamen und bewahrt ID sowie gewählte Quellroute im Snapshot. Keine Umdeutung, Titelkorrektur oder globale Sprachersetzung.

Die tatsächliche gebündelte OpenMW0.51-API dokumentiert `Cell.displayName`, `Cell.name`, `Cell.region`, `core.regions.records[regionId]` und `RegionRecord.name`. Der Builder bindet die gelesene lokale API per Digest. Die entsprechende Primärdokumentation ist [OpenMW0.51 core](https://openmw.readthedocs.io/en/openmw-0.51.0/reference/lua-scripting/openmw_core.html). API-Dokumentation und Modelltests ersetzen die getrennte native Beobachtung nicht.

## Integration in die eigene Probe

Der bereits vorhandene Presentation-Content `Veyra-Presentation.omwscripts` bleibt einmal registriert. Nach seinem bisherigen Data-Layer kommt nur:

```text
data="<presentation-candidate>/hud-014-candidate/mod"
```

Es gibt keine zweite Scriptregistrierung und keine neue ESP. Das vorhandene eigene98B-PNG wurde mit exakt demselben gebundenen eigenen Generator separat erzeugt und liegt hier bei. Die VFS-Überlagerung tauscht ausschließlich die eigene Datei `scripts/veyra/hud.lua` aus; die PNG-Bytes bleiben identisch. Root kann beide Dateien stattdessen in seine getrennte Testkopie übernehmen. Globale Profile, bisherige eingefrorene Varianten und Weltbytes bleiben unangetastet.

Die Auswahl ist: nichtleerer `cell.displayName`, danach nichtleerer `cell.name`, danach vorhandener `core.regions.records[cell.region].name`, danach die bisherige Roh-ID, zuletzt `Vvardenfell`. Eine fehlende Region oder ein Lookupfehler verdeckt keine gültige Statistik. Rohlabel werden nicht getrimmt oder sprachlich normalisiert.

`I.VeyraPresentation.getState()` ergänzt `labelSource` mit der expliziten Route und `regionId` unabhängig vom sichtbaren `cell`-Label. Der ARRIVED-only Footer lautet `[K] Sendung annehmen`, exakt an die eigene Courier0.2.4-Quellenkopie gebunden. Key-Konfliktprüfung und echte Claim-Wirkung sind Gameplay-/Root-Prüfschritte; der HUD-Modelltest beobachtet nur den passenden sichtbaren Hinweis. Menü-Hiding bei dt0, Statistik, Fenstergröße und übrige Darstellung stammen aus0.1.3.

Native-Prüfpunkt: in einer unbenannten eigenen Frontier-Zelle Engine-`cell.region`, `core.regions.records[cell.region].name` und HUD-`cell/labelSource/regionId` lesen. Sichtbild sollte `LEVIATH Frontier` zeigen und `REGION_RECORD_NAME` tragen. Eine benannte Entry-Zelle muss weiter ihren Cellnamen zeigen. Originalzellen behalten die Engine-Anzeigefassung, einschließlich `.cel`-Lokalisierung. Native Rendering und menschliche Lesbarkeitsabnahme bleiben bis zu Root-Receipt offen.

## Neubau und Lizenz

`build-label.py --base-hud <eigene eingefrorene0.1.3 Datei> --engine-api <gebündelte0.51 core.lua> --courier-key-source <eigene gebundene Courier0.2.4 Datei>` lehnt andere Eingabedigests ab. Der Generator schreibt ausschließlich hierhin. `CHECK_HUD_LABEL.sh` führt die13 bestehenden und7 zusätzlichen eigenen Lua5.1-Modellfälle aus; Engine-Pakete sind deklarierte Doubles. `build-assets.py` und `check-assets.py` stammen exakt aus dem eigenen PNG0.1.2-Generatorstand und prüfen CRC,32²RGBA und alle weißen Pixel. Alle neuen Code-/Textdateien sind MIT, keine Original-Spieldatei wurde kopiert.
