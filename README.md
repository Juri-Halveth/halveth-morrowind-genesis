# HALVETH Morrowind Genesis · 0.4.0

Erweiterungen für **The Elder Scrolls III: Morrowind** in der vorhandenen OpenMW-0.51-Installation. Morrowind, Tribunal, Bloodmoon, Vvardenfell und deine vorhandenen Figuren bleiben die Spielwelt.

## Spielen

Nach der Einrichtung startet `python launcher.py --play --profile beauty` direkt Morrowind mit dem Grafikprofil Scarlet Beauty und dem lokalen Gesprächsbegleiter im Hintergrund. Lade deinen Spielstand im normalen Hauptmenü. Die benötigte Ordnerstruktur und wählbare Installation sind in [docs/SETUP.md](docs/SETUP.md) beschrieben. Der Windows-Einstieg **Morrowind - HALVETH** lässt sich mit der vorhandenen nativen Workshop-Buildumgebung ergänzen.

- **F8:** mit JARVIS oder dem gewählten NPC sprechen; Heilen, +250 Gold, Startpunkt und Zurück nutzen.
- **F7** oder **Wissen** im F8-Fenster: Wissensjournal, Bibliothek und Alchemiehilfe.
- **Bücher / B:** sechs eigene Bücher zum Inventar hinzufügen. Öffne sie im normalen Buch- oder Schriftrollenfenster.
- **LOVE / SPARK / AEGIS / M:** drei Zauber lernen. Auswählen und mit den normalen Morrowind-Zaubertasten einsetzen.
- **Studieren / S:** eine gelesene Notiz merken. Ein Alchemietext unterstützt die nächste erfolgreiche Trankpraxis einmalig um 5–10 Prozent.
- **F2:** die vorhandenen Shaderregler öffnen.

Der Begleiter benötigt das bereits installierte lokale Ollama-Modell `hermes3:8b`. Ist der Dienst nicht erreichbar, startet Morrowind weiter offline; Wissen, Bücher und direkte Spielwerkzeuge bleiben verfügbar. Der reguläre Einstieg öffnet weder einen Browser noch ein zusätzliches Konfigurationsfenster.

## Wissen und Magie in Morrowind

Das Journal registriert geöffnete Bücher und Schriftrollen anhand ihres Spiel-Datensatzes. Es merkt die Anzeigezeit im Buchfenster, Studiennotizen und verbrauchte Praxisboni im normalen Spielstand. Anzeigezeit ist kein gemessenes Textverständnis. Es gibt keinen Mindesttimer und keine XP allein fürs Offenlassen eines Buches.

Die sechs eigenen Bücher enthalten 15 verfasste Textabschnitte und passende Lernfragen. Morrowind bestimmt die sichtbare Seiteneinteilung. Eigene alchemistische Rezepte aus diesen Geschichten sind zunächst Weltbeschreibung; Zutatenhilfe und Trankherstellung verwenden tatsächlich vorhandene Morrowind-Zutaten und -Effekte.

| Zauber | Wirkung | Magicka |
|---|---|---:|
| LOVE | 6 Gesundheit pro Sekunde für 5 Sekunden | 8 |
| SPARK | Schockprojektil mit 12–18 Schaden | 10 |
| AEGIS | 20 Schildpunkte für 30 Sekunden | 12 |

Bücher und Zauber werden über die jeweiligen Schaltflächen angefordert. Vorhandene Exemplare und gelernte Zauber werden dabei nicht dupliziert. Die Alchemiehilfe zeigt passende Zutatenpaare aus dem aktuellen Inventar; gebraut wird im gewohnten Alchemiefenster.

## Gespräche und Spielwerkzeuge

Die NPC-Auswahl bevorzugt das aktuelle Dialogziel, dann das anvisierte Wesen und schließlich das nächste Wesen. Der Begleiter erhält begrenzten Kontext zu Ort, Figur, Zustandswerten, Quests und dem zuletzt geöffneten Buch. Erinnerungen sind je Kampagne und Figureninstanz getrennt.

Die Lore-Bibliothek entsteht lokal aus deiner eigenen Spielinstallation. Im öffentlichen Quellpaket stehen drei ursprüngliche Projektfiguren und acht selbst formulierte Designkarten. Extrahierte Bücher, Dialoge, Spielstände und Gesprächserinnerungen werden nicht ausgeliefert. Für eine einzelne Antwort verwendet das Modell einen begrenzten Ausschnitt; erzeugter Dialog ist kein Ersatz für die vorhandene Questlogik.

**Startpunkt** bezeichnet den Ort beim Laden der Sitzung. **Zurück** führt an den vor der letzten Teleportation gespeicherten Ort. Die Schaltfläche **+250 Gold** ist ein zusätzliches Werkzeug. Der historische Vivec-Glitch bleibt separat in [docs/VIVEC-GOLD.md](docs/VIVEC-GOLD.md) dokumentiert.

## Grafik und bestehende Spielstände

Scarlet Beauty kann lokal installierte Kopf- und Haarmodelle, Landschaftstexturen, Sternenhimmel und Shader für Schatten, Wolken, Wasser und Nachbearbeitung verbinden. Diese Drittanbieterpakete sind nicht enthalten. Das eigene LOVE-Motiv erscheint im F8-Fenster und als optionaler Wandbehang. Der Kopfadapter ändert Modelldarstellungen, keine NPC-, Quest- oder Inventardatensätze.

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
python scripts/build_release.py
```

Die optionalen Integrationstests benötigen die eigene OpenMW-/Morrowind-Installation. Sie verwenden eigene Testsitzungen statt persönlicher Spielstände. `.local/` enthält persönliche Daten, Sicherungen und Testbelege und gehört nicht ins öffentliche Repository.

Die [native Prüfzusammenfassung für 0.4](docs/NATIVE-VERIFICATION-0.4.0.json) bindet Inhalts-, Speicher-, Zauber- und Gesprächsprüfungen an ihre jeweiligen Quellenstände. Das abschließend überarbeitete Wissensfenster wurde im Spiel mit Mausbedienung betrachtet; die davor geprüfte Speicher-/Bonuslogik und diese spätere UI-Fassung tragen getrennte Hashes. Physische F7-/F8-Tasteneingaben wurden nicht verifiziert.

## Weiterer Ausbau

Weitere friedliche Questverzweigungen, ein Bausystem, neue Regionen, umfassende Bewegungs- und Kampfänderungen sowie individuelle Stimmen bleiben Entwicklungsarbeit **an Morrowind**. Die getrennten Realms-/Portal-Garden-Prototypen sind eingestellt; verwendbare Inhalte werden für diese Spielwelt portiert. Unreal-Rendererfunktionen sind durch die Portierung von Büchern oder Spielregeln nicht automatisch in OpenMW vorhanden.

## Lizenz und Veröffentlichung

Eigener Code und eigene Texte: **MIT**. Die ausdrücklich benannten LOVE-Grafikdateien: **CC0-1.0**, siehe [ASSET-LICENSE.md](ASSET-LICENSE.md). Spenden sind freiwillig. Originale Spieldaten, andere Mods, Engine und Sprachmodelle behalten ihre jeweiligen Bedingungen.

Die bisherige öffentliche Fassung liegt im [Morrowind-Repository](https://github.com/Juri-Halveth/halveth-morrowind-genesis). Diese Version 0.4 wird lokal gebaut und geprüft; ein lokales Paket allein bedeutet noch keine veröffentlichte Version.
