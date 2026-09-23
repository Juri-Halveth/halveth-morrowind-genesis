# HALVETH Morrowind Genesis · 0.9.0

Erweiterungen für **The Elder Scrolls III: Morrowind** in der vorhandenen OpenMW-0.51-Installation. Morrowind, Tribunal, Bloodmoon, Vvardenfell und deine vorhandenen Figuren bleiben die Spielwelt.

## Spielen

Nach der Einrichtung startet `python launcher.py --play --profile beauty` direkt Morrowind mit dem Grafikprofil Scarlet Beauty und dem lokalen Gesprächsbegleiter im Hintergrund. Lade deinen Spielstand im normalen Hauptmenü. Die benötigte Ordnerstruktur und wählbare Installation sind in [docs/SETUP.md](docs/SETUP.md) beschrieben. Der Windows-Einstieg **Morrowind - HALVETH** startet dieselbe Welt. Das öffentliche Quellpaket liefert keine Bethesda-Spieldaten.

Für Windows gibt es [eine eigenständige Setup-EXE mit LOVE-Symbol](installer/README.md): Die öffentliche Kandidatenvariante installiert die eigene Erweiterung und benötigt OpenMW 0.51; die private lokale Variante enthält zusätzlich die bereits vorhandene OpenMW-Engine. Beide binden Morrowind aus deiner lizenzierten Installation ein, lassen Originaldateien und Saves am Quellort und erzeugen einen sichtbaren Spieleinstieg. Die laufende OpenMW-Engine und ihre Ressourcen bleiben nach der Installation technisch separate Dateien; das Setup ist eine einzige EXE, keine behauptete Ein-Datei-Ausgabe des gesamten Bethesda-Spiels.

- **F6** oder **HALVETH · Figur** im normalen Inventar/Dialog: Figur, Inventar, Magie und Begegnungen öffnen.
- **F8:** mit JARVIS oder dem gewählten NPC sprechen; Heilen, +250 Gold, Startpunkt und Zurück nutzen.
- **F7** oder **Wissen** im F8-Fenster: Wissensjournal, Bibliothek und Alchemiehilfe.
- **Pfade** in der nativen Menüleiste: drei zusätzliche Ziele für echte Bücher, Begegnungen und Orte; die vorhandenen Quests bleiben erhalten.
- **Sammeln** in der nativen Menüleiste öffnet den Sammelatlas: lose Zutaten in der geladenen Morrowind-Welt finden, ihren Ort notieren und ein Ziel im Spielbild verfolgen.
- **Weltleben** in der nativen Menüleiste: beobachtete Figuren und regionale Fraktionsimpulse im Spiel verfolgen.
- **Sprechen** im Weltleben-Fenster: eine noch nahe beobachtete Figur unmittelbar im nativen Gesprächsfenster ansprechen.
- **Licht** in der nativen Menüleiste: den eigenen HALVETH-Filter zwischen Scharlachlicht, Morgenrot, Lebendige Welt, Nachtglas und Original umschalten.
- **Sicht** im normalen Inventar- oder Dialogmenü: zwischen Ich-Sicht, Außen-Sicht und freiem Blick wechseln; Kamera drehen, Abstand ändern und zur vorherigen Ansicht zurückkehren.
- **Bücher / B:** sechs eigene Bücher zum Inventar hinzufügen. Öffne sie im normalen Buch- oder Schriftrollenfenster.
- **LOVE / SPARK / AEGIS / M:** drei Zauber lernen. Auswählen und mit den normalen Morrowind-Zaubertasten einsetzen.
- **Studieren / S:** eine gelesene Notiz merken. Ein Alchemietext unterstützt die nächste erfolgreiche Trankpraxis einmalig um 5–10 Prozent.
- **F2:** die vorhandenen Shaderregler öffnen.

Der Begleiter benötigt das bereits installierte lokale Ollama-Modell `hermes3:8b`. Ist der Dienst nicht erreichbar, startet Morrowind weiter offline; Wissen, Bücher und direkte Spielwerkzeuge bleiben verfügbar. Der reguläre Einstieg öffnet weder einen Browser noch ein zusätzliches Konfigurationsfenster.

## Figur, Ausrüstung und Begegnungen

Das neue F6-Fenster arbeitet mit den tatsächlichen Daten deiner Spielfigur. Es erklärt alle 27 Fertigkeiten, zeigt Attribute und Zustandswerte, durchsucht das aktuelle Inventar und sortiert Gegenstände wahlweise nach Name oder Wert pro Gewicht. Zwölf Gegenstandskategorien liefern passende Details, etwa Waffenschaden, Zustand, Verzauberung oder die durch Alchemie bereits erkennbaren Zutateneffekte.

Unter **Magie** stehen die aktuell erlernten Zauber mit Kosten, Reichweite, Dauer und Wirkung. **Zauber auswählen** setzt die normale Morrowind-Auswahl; anschließend zauberst du wie gewohnt. Unter **Begegnungen** findest du geladene Figuren im Umkreis von 3.000 Spieleinheiten und kannst gezielt mit einer davon sprechen. Bücher öffnen ihren vorhandenen Buch- oder Schriftrollenleser. Die Schaltflächenleiste im normalen Inventar und Dialog macht F6, F7 und F8 auch per Maus erreichbar.

NPC-Gespräche erhalten Beruf, Dienste, Zugehörigkeiten, Verletzung und aktuelle Sympathie aus dem Spiel. Ein stabiler eigener Sprechstil ergänzt diese Daten und das getrennte Gesprächsgedächtnis. Die Stilauswahl ist Inszenierung; sie fügt keine erfundene Originalbiografie hinzu. Das lokale Modell kann weiterhin sprachliche und inhaltliche Fehler machen.

## Wissen und Magie in Morrowind

Das Journal registriert geöffnete Bücher und Schriftrollen anhand ihres Spiel-Datensatzes. Es merkt die Anzeigezeit im Buchfenster, Studiennotizen und verbrauchte Praxisboni im normalen Spielstand. Anzeigezeit ist kein gemessenes Textverständnis. Es gibt keinen Mindesttimer und keine XP allein fürs Offenlassen eines Buches.

Die sechs eigenen Bücher enthalten 15 verfasste Textabschnitte und passende Lernfragen. Morrowind bestimmt die sichtbare Seiteneinteilung. Eigene alchemistische Rezepte aus diesen Geschichten sind zunächst Weltbeschreibung; Zutatenhilfe und Trankherstellung verwenden tatsächlich vorhandene Morrowind-Zutaten und -Effekte.

Version 0.6 ergänzt im Wissensfenster einen **Rezeptplaner**. Er verbindet nur Zutaten aus dem aktuellen Inventar, deren gemeinsamen Effekt die Spielfigur nach ihrem tatsächlichen Alchemiewert schon erkennen darf. Du kannst ein Paar auswählen und im Spielstand merken; **Brauen** führt zum normalen Morrowind-Alchemiefenster. Verbrauch, Erfolg und Trank bleiben Regeln des Originalspiels. Ein gemerktes Rezept stellt keinen Trank von selbst her.

Version 0.7 ergänzt einen **Sammelatlas** für lose, tatsächlich geladene Zutaten in der näheren Umgebung. Er zeigt Name, ungefähre Entfernung und Himmelsrichtung, merkt eine Zutatenart pro Ort einmalig im Spielstand und kann ein sichtbares Sammelziel im normalen Spielbild markieren. Der Atlas durchsucht keine fremden Inventare oder geschlossenen Behälter. Aufheben und Alchemie bleiben die normalen Morrowind-Handlungen.

| Zauber | Wirkung | Magicka |
|---|---|---:|
| LOVE | 6 Gesundheit pro Sekunde für 5 Sekunden | 8 |
| SPARK | Schockprojektil mit 12–18 Schaden | 10 |
| AEGIS | 20 Schildpunkte für 30 Sekunden | 12 |

Bücher und Zauber werden über die jeweiligen Schaltflächen angefordert. Vorhandene Exemplare und gelernte Zauber werden dabei nicht dupliziert. Die Alchemiehilfe zeigt passende Zutatenpaare aus dem aktuellen Inventar; gebraut wird im gewohnten Alchemiefenster.

## Drei neue Spuren in derselben Welt

**Spur des Wissens** zählt zwei verschiedene gelesene Texte und eine Begegnung. **Spur der Begegnung** zählt zwei verschiedene angesprochene Figuren und einen neu betretenen Ort. **Spur der Welt** verbindet drei Orte mit einem gelesenen Text. Das native Fenster zeigt jede Spur als **Neu**, **In Arbeit** oder **Erledigt**; Fortschritt gehört zum normalen Spielstand. Eine abgeschlossene Spur bietet einmalig bis zu 30 Ausdauerpunkte. Offenlassen einer Seite oder wiederholtes Anklicken derselben Figur erzeugt keinen zusätzlichen Fortschritt. Diese drei eigenen Wege setzen keine Bethesda-Queststufe um und ersetzen keine Handlung des Originalspiels.

## Gespräche und Spielwerkzeuge

Die NPC-Auswahl bevorzugt das aktuelle Dialogziel, dann das anvisierte Wesen und schließlich das nächste Wesen. Der Begleiter erhält begrenzten Kontext zu Ort, Figur, Zustandswerten, Quests und dem zuletzt geöffneten Buch. Erinnerungen sind je Kampagne und Figureninstanz getrennt.

Version 0.8 führt eine **native Weltleben-Chronik** ein. Sie merkt sich tatsächlich geladene und in der Nähe gesehene NPCs, wiederholte Begegnungen an anderen Orten sowie echte Gespräche im Spielstand. Ein regionaler Fraktionsimpuls ist eine klar getrennte neue Spielregel aus diesen Beobachtungen; er behauptet keine ungesehenen politischen Ereignisse. Der lokale Gesprächsbegleiter erhält daraus einen begrenzten Kontext. Die Original-Fraktionswerte und Queststufen werden nicht durch die Chronik verändert.

Mit **Rufen** kann draußen ein eigener HALVETH-Wanderer entstehen. Er bewegt sich mit einem nativen OpenMW-Wanderpaket und kann pausiert, fortgesetzt oder gezielt entfernt werden. Die Original-NPCs bleiben unverändert. [Spielregel und Grenzen](docs/WORLDLIFE-0.8.md).

Version 0.8.1 verbindet die Chronik direkt mit dem Gespräch: Figur auswählen, **Sprechen** anklicken, Unterhaltung beginnen. Ist die Figur nicht mehr in der geladenen Umgebung, bleibt das Weltleben-Fenster offen und meldet dies. Die sieben Aktionsknöpfe passen sich der Fensterbreite an. Der Weg wurde mit Arrille in einer isolierten OpenMW-Sitzung einschließlich Speichern/Laden geprüft.

Version 0.9 ergänzt eine **native Spielerperspektive**. Die Kamera folgt weiterhin deiner Figur in derselben Morrowind-Welt; im Sicht-Fenster schaltest du Ich-Sicht, Außen-Sicht oder freien Blick um und drehst oder zoomst die Kamera. Das Fenster zeigt bis zu sechs geladene Figuren, deren Position in den aktuellen Bildausschnitt projiziert wird. Dieser begrenzte Blickkontext erreicht auch den lokalen Gesprächsbegleiter. Eine Projektion prüft weder Sichtlinien noch die Gedanken anderer Figuren. [Bedienung, Quellen und Grenzen](docs/PLAYER-PERSPECTIVE.md).

Die Lore-Bibliothek entsteht lokal aus deiner eigenen Spielinstallation. Im öffentlichen Quellpaket stehen drei ursprüngliche Projektfiguren und acht selbst formulierte Designkarten. Extrahierte Bücher, Dialoge, Spielstände und Gesprächserinnerungen werden nicht ausgeliefert. Für eine einzelne Antwort verwendet das Modell einen begrenzten Ausschnitt; erzeugter Dialog ist kein Ersatz für die vorhandene Questlogik.

**Startpunkt** bezeichnet den Ort beim Laden der Sitzung. **Zurück** führt an den vor der letzten Teleportation gespeicherten Ort. Die Schaltfläche **+250 Gold** ist ein zusätzliches Werkzeug. Der historische Vivec-Glitch bleibt separat in [docs/VIVEC-GOLD.md](docs/VIVEC-GOLD.md) dokumentiert.

## Grafik und bestehende Spielstände

Scarlet Beauty kann lokal installierte Kopf- und Haarmodelle, Landschaftstexturen, Sternenhimmel und Shader für Schatten, Wolken, Wasser und Nachbearbeitung verbinden. Diese Drittanbieterpakete sind nicht enthalten. Das eigene LOVE-Motiv erscheint im F8-Fenster und als optionaler Wandbehang. Version 0.7 zeigt im F8-Fenster ein neu generiertes LOVE-Astrolabium als Originalmotiv. Der Kopfadapter ändert Modelldarstellungen, keine NPC-, Quest- oder Inventardatensätze.

Version 0.5 ergänzt eine geglättete Schriftkonfiguration für das bereits mit OpenMW ausgelieferte MysticCards. Die Schriftdatei selbst wird nicht mitgeliefert. Das Menü verwendet die nativen Morrowind-Rahmen und läuft innerhalb des Spiels. Version 0.6 ergänzt einen **eigenen OpenMW-Nachbearbeitungsfilter**; 0.7 erweitert ihn um das deutlich kräftigere **Morgenrot**. Version 0.8 ergänzt **Lebendige Welt**: Der Filter liest im Freien Sonnenanteil und Sturmstatus aus dem Spiel und passt seine Farbgebung laufend an. Vier Modi färben die Szene; **Original** deaktiviert den eigenen Filter. Die Spielwelt-Assets und OpenMWs Renderer werden dabei nicht ersetzt. [Technik und Grenzen des Filters](docs/VISUAL-ATMOSPHERE.md).

Die Erweiterung nutzt ein eigenes OpenMW-Profil. Spielstandkopien sind im öffentlichen Launcher standardmäßig aus; `--copy-saves` übernimmt ausdrücklich für diesen Start fehlende Kopien, ohne vorhandene Dateien zu überschreiben. Masterdateien und ursprüngliche Saves bleiben erhalten. Bestehende Grafik-, Sound- und Eingabeeinstellungen des Profils werden beim normalen Start beibehalten. Details: [docs/GRAPHICS.md](docs/GRAPHICS.md).

## Entwicklung

`mod/scripts/halveth/` enthält die direkt im Spiel laufenden Lua-Erweiterungen. `data/native-content.json` ist die Quelle der eigenen Bücher und Zauber. `server.py` verbindet das Spiel im Hintergrund mit lokalem Modell und Gedächtnis. `native/GenesisEntry.cs` und `scripts/build_native_entry.py` erstellen den nativen Spieleinstieg mit der vorhandenen Windows-Buildumgebung.

```text
python launcher.py --play --profile beauty
python -m unittest discover -s tests -p "test_*.py"
python tests/integration_content.py
python tests/integration_knowledge.py
python tests/integration_cast.py
python tests/integration_chat.py
python tests/integration_chat.py --npc
python tests/integration_universe.py
python tests/integration_paths.py
python tests/integration_visuals.py
python tests/integration_visuals.py --cell "Seyda Neen" --expect-source weather
python tests/integration_perspective.py
python tests/integration_fieldcraft.py
python tests/integration_worldlife.py
python tests/integration_actor_life.py
python tests/integration_art_070.py
python scripts/survey_universe.py --help
python scripts/build_release.py
```

Die optionalen Integrationstests benötigen die eigene OpenMW-/Morrowind-Installation. Sie verwenden eigene Testsitzungen statt persönlicher Spielstände. `.local/` enthält persönliche Daten, Sicherungen und Testbelege und gehört nicht ins öffentliche Repository.

Die [native Prüfung für 0.9](docs/NATIVE-VERIFICATION-0.9.0.json) bindet einen frischen OpenMW-Lauf mit allen drei Kameramodi, deren Fortbestand über weitere Frames, Drehen, Zoom, nativem Sicht-Fenster und gekennzeichnetem Blickkontext. Die bestehende F6-Ansicht wurde danach separat mit echter Figur, 27 Fertigkeiten, Inventar, Zauber und Begegnungen erneut geprüft. Ein persönlicher Spielstand wurde dabei nicht geladen.

Die [native Prüfzusammenfassung für 0.8](docs/NATIVE-VERIFICATION-0.8.0.json) bindet vier neue isolierte OpenMW-Läufe: beobachtete NPCs samt Dialog- und Speicherstand, einen tatsächlich wandernden eigenen NPC mit Pause/Weiter/Entfernen sowie den Fünf-Modi-Shader im Innen- und Außenraum mit realem Sonnenwert. Der private Installer wurde zusätzlich in eigenen frischen Spielsitzungen geprüft. Ein persönlicher Spielstand wurde für 0.8 nicht geladen; die neuen Skripte gelten beim nächsten normalen Spielstart.

Die [native Prüfzusammenfassung für 0.7](docs/NATIVE-VERIFICATION-0.7.0.json) bindet drei isolierte OpenMW-Läufe: Sammelatlas mit echter loser Zutat, HUD und Speichern/Laden; alle vier Lichtzustände samt aktivem Shader; die tatsächliche Auswahl der neuen PNG im nativen F8-Fenster. Der bestehende persönliche Spielprozess wurde vor 0.7 gestartet; die neuen Skripte laden bei seinem nächsten normalen Start. Das neue Mausfeld wurde in der persönlichen Spielsession noch nicht separat angeklickt.

Die [native Prüfzusammenfassung für 0.6](docs/NATIVE-VERIFICATION-0.6.0.json) bindet vier isolierte OpenMW-Läufe: Pfade mit echtem Speichern und Laden, Rezeptplaner mit Übergabe an das normale Alchemiefenster, den aktiven eigenen Shader und die bisherige F6-Weltansicht. Im vorhandenen Morrowind-Spielstand wurden die neue Mausleiste für Pfade, Wissen und alle drei Lichtmodi bedient; zwei geprüfte Spielstanddateien blieben unverändert. Die [Prüfungen für 0.5](docs/NATIVE-VERIFICATION-0.5.0.json) dokumentieren zusätzlich einen echten Arrille-Modellrundlauf; [0.4](docs/NATIVE-VERIFICATION-0.4.0.json) bleibt als historischer Stand erhalten. Physische F6-/F7-/F8-Tasteneingaben sind weiter unbestätigt.

`survey_universe.py` liest sämtliche Datensatz- und Unterdatensatzgrenzen der aktiven TES3-Plugins und baut lokal ein versionsgebundenes Register. Das Register und extrahierte Inhalte bleiben privat. Eine vollständige Strukturaufnahme dieser Plugins ist keine vollständige Prüfung sämtlicher Skriptpfade, Texturen oder Animationen. Umfang und weitere Entwicklungsäste stehen in [docs/UNIVERSE-0.5.md](docs/UNIVERSE-0.5.md).

## Weiterer Ausbau

Weitere friedliche Questverzweigungen, ein Bausystem, neue Regionen, umfassende Bewegungs- und Kampfänderungen sowie individuelle Stimmen bleiben Entwicklungsarbeit **an Morrowind**. Die getrennten Realms-/Portal-Garden-Prototypen sind eingestellt; verwendbare Inhalte werden für diese Spielwelt portiert. Unreal-Rendererfunktionen sind durch die Portierung von Büchern oder Spielregeln nicht automatisch in OpenMW vorhanden.

Die [Designübertragung aus New World und weiteren Vorbildern](docs/NEW-WORLD-DESIGN-TRANSFER.md) trennt eigene Morrowind-Funktionen von späteren Ideen und dokumentiert die aktuelle Rechteprüfung. Sie verwendet öffentliche Mechanikbeschreibungen als Anregung. New-World-Quellcode, Texturen, Modelle und Datenbankeinträge sind nicht enthalten.

## Lizenz und Veröffentlichung

Eigener Code und eigene Texte: **MIT**. Die ausdrücklich benannten LOVE-Grafikdateien: **CC0-1.0**, siehe [ASSET-LICENSE.md](ASSET-LICENSE.md). Spenden sind freiwillig. Originale Spieldaten, andere Mods, Engine und Sprachmodelle behalten ihre jeweiligen Bedingungen.

Quellstand, Prüfungen und veröffentlichte Pakete stehen im [Morrowind-Repository](https://github.com/Juri-Halveth/halveth-morrowind-genesis). Den Veröffentlichungsstand einer Version zeigt die [Release-Liste](https://github.com/Juri-Halveth/halveth-morrowind-genesis/releases); ein lokales Paket allein bedeutet noch keine Veröffentlichung.
