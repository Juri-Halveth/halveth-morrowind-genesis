# Scarlet Atelier · Genesis 0.3.0

Die Erweiterung verbindet ein eigenes generiertes Motiv, den nativen OpenMW-Dialog und einen kleinen, quellengebundenen Wissensbestand. Sie läuft auf der vorhandenen Genesis-Installation. HALVETH Realms bleibt ein anderes Spielprojekt.

## Jetzt benutzen

Im Genesis-Launcher **Scarlet Beauty → Genesis spielen** starten. **F8** öffnet das Gesprächsfenster mit dem neuen Motiv. Im **Konstellarium → Atelier** stehen die Bildansicht, drei kopierbare Produktionsbriefs, fünf Werkzeugwege und acht GitHub-Quellenkarten. Die vorhandenen Aktionen Heilen, +250 Gold, Startpunkt und Zurück bleiben verfügbar.

Die lokale Companion-Adresse ist `http://127.0.0.1:18765/`. Ein Spielneustart lädt neue Texturen; ein bloßes Neuladen des Browsers reicht dafür nicht.

## Das neue Motiv im Spiel

Der Wandbehang ist eine eigene Imagegen-Arbeit mit rotem Rankenherz, goldenem Portal, Mottenflügeln und Pilzornamenten. Der Generator lieferte **887 × 1774 Pixel**, exakt 1:2. Die tatsächlich installierte Größe ist damit ausdrücklich kleiner als das im Produktionsbrief gewünschte 1024 × 2048. PNG, TGA und DDS enthalten denselben Entwurf; die Konvertierung ändert weder Motiv noch Maße.

Das zusätzliche Verzeichnis `.local/graphics/ScarletLoveBanner` überschreibt ausschließlich `Textures/Tx_de_tapestry_02.tga` und `.dds`. Dadurch ändern sich **alle Vorkommen dieses einen Wandbehangtyps**. Das Motiv ersetzt keinen Charakter und schreibt keine Quest-, NPC-, Gold- oder Inventardatensätze. Das PNG im eigenen Namensraum begleitet die F8-Oberfläche.

Die DDS-Datei ist erforderlich: OpenMW 0.51 sucht bei der Texturauflösung zuerst nach der DDS-Alternative. In der vorhandenen `Morrowind.bsa` liegt eine alte DDS gleichen Namens; allein die neue TGA war deshalb im Spiel nicht sichtbar. Die Korrektur folgt dem [versionsgebundenen Engine-Code](https://github.com/OpenMW/openmw/blob/openmw-0.51.0/components/misc/resourcehelpers.cpp).

Ein- und Ausschalten für Entwickler:

```text
python scripts/install_scarlet_banner.py apply
python scripts/prepare_profile.py --profile beauty
python scripts/prepare_profile.py --profile cinematic
```

Zum Rückwechsel `restore` statt `apply` ausführen und beide Profile erneut vorbereiten. Das entfernt nur den Eintrag dieses Packs aus dem Grafikmanifest. Andere spätere Grafikänderungen und die eigenen Assetdateien bleiben erhalten; Backups liegen bei den Installationsbelegen. Das F8-PNG bleibt als eigenständige Oberfläche sichtbar. Persönliche Spielstände werden dabei nicht geladen.

## Wissensaufnahme

`data/project-knowledge.json` enthält acht eigene Paraphrasen mit Repository, Commit, Quelldatei, Zeilen und Abrufzeit. Themen sind LOVE, Figurenregister, ASTER-Erinnerung, gemeinsame Fragen, gewählte Reise, Lernen, Portal und Maßstäbe im Weltdesign.

Jede Antwort erhält höchstens drei passende Karten mit zusammen höchstens 6.500 Zeichen. Die Karten sind **Designreferenzen**. Sie ergänzen die getrennte Morrowind-Lore und werden nicht als Bücher oder geschehene Spielereignisse ausgegeben. Bei erfolgreichem Modellaufruf zeigt das Browsergespräch die übergebenen Projektquellen an. Im Offlinepfad bleiben diese Modellverweise leer. Reine JARVIS-Anreden lösen keine Karte aus.

Die Quellen wurden über den verbundenen GitHub-Zugang frisch gelesen. Das ist eine begrenzte Auswahl öffentlicher Projekte, keine Aufnahme sämtlicher GitHub-Dateien oder des gesamten WWW. Der private Lore-Index mit 36.227 Zeilen bleibt lokal. Das lokale Modell kann trotz Herkunftsangaben falsche oder zu lange Antworten erzeugen; der zweite Design-Fragetest erreichte das bestehende Ausgabelimit.

## Weitere Produktionswege

[GENERATION-PIPELINE.md](GENERATION-PIPELINE.md) bindet Adobe, Meshy, Dreamina/Seedance und Blender an konkrete Dateiformate. Die drei Briefs sind sofort kopierbar. Modell- und Filmaufträge bei diesen Anbietern wurden nicht gestartet; Kontozugänge, Credits und Exporte sind jeweils gesonderte Voraussetzungen. Das hier installierte Motiv wurde mit dem verfügbaren Imagegen-Werkzeug erstellt.

Das aktuelle Paket ist eine lokale Mod-/Quellcodefassung. Es enthält keine neue vollständige Morrowind-EXE und wurde nicht als Genesis-Release auf GitHub veröffentlicht. Die ältere eigenständige Realms-EXE ersetzt es nicht. Öffentliche Lizenz- und Vertriebsentscheidungen bleiben in `LICENSE-DECISION.md` geführt.

## Prüfungen

Die Tests verwenden frische Spielwelten und getrennte temporäre Datenbanken. Die native Sichtprüfung fand in **Suran, Suran Temple** am Objekt `furn_de_tapestry_02` statt. Die erste TGA-Prüfung wurde durch die DDS-Sichtprüfung ergänzt; ein bestandener Dateitest allein wurde nicht als erfolgreiches Rendering ausgegeben.

Die Einzelresultate des aktuellen Standes stehen in `BUILD-0.3.0.json`. Frühere `BUILD-RESULT.json` und `GRAPHICS-RESULT.json` dokumentieren weiterhin den älteren 0.2-Stand; die damalige kurze FPS-Messung ist keine neue Messung dieser Erweiterung.
