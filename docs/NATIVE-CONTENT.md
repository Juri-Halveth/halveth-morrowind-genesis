# Eigene Inhalte direkt in Morrowind

Diese Erweiterung laeuft als Lua-Mod in TES III Morrowind mit der vorhandenen OpenMW-Engine 0.51. Sie erzeugt echte `BOOK`- und `SPEL`-Datensaetze innerhalb dieser Spielwelt. Die Buecher benutzen Morrowinds normales Inventar und Buch-/Schriftrollenfenster; die Zauber erscheinen im normalen Zaubermenue. Es wird kein zweites Spiel und kein Browserfenster geoeffnet.

Im Wissen-Fenster koennen die Schaltflaechen **Eigene Buecher** und **LOVE / SPARK / AEGIS** bewusst gewaehlt werden. Es gibt keine automatische Vergabe beim Laden eines bestehenden Spielstands. Die sechs Buecher haben keinen Verkaufswert; ein erneuter Klick ergaenzt fehlende Exemplare, ohne vorhandene zu duplizieren. Bekannte Zauber werden nicht doppelt hinzugefuegt. Mit dem normalen Speichern bewahrt OpenMW die erzeugten Datensaetze und das Inventar.

## Buecher

| Eigenes Werk | Form | Thema | Eigene Abschnitte |
| --- | --- | --- | ---: |
| The Glassleaf Primer | Buch | Alchemie | 3 |
| Ink Between Stars | Buch | Verzauberung | 3 |
| A House Needs Three Supports | Buch | Handwerk | 3 |
| A Scroll of Moonwater Accounts | Schriftrolle | Alchemie | 2 |
| A Margin Full of Quiet Signals | Notizrolle | Verzauberung | 2 |
| Minutes of an Unfinished Garden | Journal | Gespraech | 2 |

Diese fuenfzehn urspruenglich fuer HALVETH geschriebenen englischen Textabschnitte sind in `data/native-content.json` erhalten. Sie sind eigene Garten-Lore. Die dort beschriebenen Glassleaf-, Lumen- und Bau-Rezepte sind Erzaehlung; dieser Inhaltsport erzeugt noch keine entsprechenden Alchemiezutaten oder Bauobjekte in Morrowind. Die native Buchdarstellung verteilt den Text nach Fenster und Schrift selbst auf Seiten. Die Passageanzahl ist deshalb keine feste Zahl angezeigter Buchseiten.

Alle sechs Werke tragen den Titelpraefix `HALVETH:`. Modelle und Inventarsymbole werden aus vorhandenen geladenen Buechern referenziert. Texte, Verzauberungen, Quests oder Skripte dieser Vorlagen werden nicht uebernommen. Es gibt keinen zusaetzlichen automatischen Vanilla-Skillbuchbonus; die Zuordnung zum Wissenssystem erfolgt getrennt ueber die bereitgestellte Record-ID und das Fachgebiet.

## Zauber

| Zauber | Native Wirkung | Ziel | Magicka |
| --- | --- | --- | ---: |
| LOVE – Heilschein | Gesundheit wiederherstellen, 6 Punkte/Sekunde fuer 5 Sekunden | Selbst | 8 |
| SPARK – Sternenfunke | Schockschaden, 12–18 Punkte fuer 1 Sekunde | Zielprojektil | 10 |
| AEGIS – Lichtwacht | Schild, 20 Punkte fuer 30 Sekunden | Selbst | 12 |

Es sind normale zauberbare Sprueche mit Magickakosten. Fuer diese drei bewusst angeforderten HALVETH-Sprueche ist die native Erfolgsgarantie gesetzt; ein Wuerfelwurf der Fertigkeit laesst sie daher nicht scheitern. Animationen, Projektile, Effekte, Kollisions- und Magielogik kommen von Morrowind/OpenMW. SPARK ist ein Schadenszauber und folgt den normalen Reaktionen auf Angriffe.

## Implementierung und reproduzierbarer Test

- `mod/scripts/halveth/content.lua`: globale native Record-Erzeugung und bewusst angeforderte Vergabe.
- `mod/scripts/halveth/content_catalog.lua`: generierte eigene Texte und Zauberkonfiguration.
- `scripts/build_native_content.py --check`: reproduzierbaren Katalog pruefen.
- `tests/integration_content.py`: neue eigene Vivec-Testszene starten, native Datensaetze und Inventar beobachten, erneut anfordern, beenden. Es wird kein bestehender Spielstand geladen oder gespeichert.
- `tests/integration_cast.py`: mit einem frischen Testcharakter LOVE und AEGIS ueber den normalen nativen Zauberpfad wirken; Gesundheitsaenderung, Schildwirkung und Magickakosten beobachten.

Am 23.09.2026 lief dieser Integrationstest tatsaechlich mit der lokal installierten OpenMW-Engine. Beobachtet wurden sechs native Buecher mit allen fuenfzehn Originalabschnitten, drei bekannte Zauber mit den oben angegebenen Effekten sowie unveraenderte Record-IDs und genau ein Buchexemplar nach erneuter Anforderung. Exit-Code `0`, keine Lua-/Engine-Fehler, keine geschriebenen `.omwsave`-Dateien. Die Ausgangskonfiguration und Einstellungen blieben hashgleich.

Der zusaetzliche native Cast-Test waehlte LOVE im normalen Zaubersystem, nahm die Zauberhaltung ein und loeste den gewoehnlichen `controls.use`-Pfad aus. Im Beobachtungsfenster stieg die Gesundheit des ausschliesslich fuer den Test erzeugten Charakters von `1` auf `19.400037765503`; Magicka sank von `50` auf `42`. Anschliessend erzeugte AEGIS einen aktiven nativen Schild mit Staerke `20` und verbrauchte weitere `12` Magicka (`42` auf `30`). Es wurden keine aktiven Effekte direkt injiziert. Auch dieser Lauf endete mit Exit-Code `0`, ohne Lua-/Engine-Fehler und ohne gespeicherten Spielstand. Zwei zuvor erhaltene Testfehlversuche betrafen die asynchrone Uebernahme der Zauberauswahl im Testablauf; die Inhaltsdateien mussten nicht geaendert werden. Physische Tasteneingabe und die sichtbare Qualitaet der Cast-Animationen sind durch diese automatisierten Beobachtungen nicht belegt.

Die verwendeten Signaturen wurden aus den installierten `resources/lua_api/openmw/{types,core,world}.lua` sowie dem gebundenen OpenMW-0.51.0-Quellarchiv geprueft: `types.Book.createRecordDraft`, `core.magic.spells.createRecordDraft`, `world.createRecord`, `world.createObject`, `Actor.inventory` und `Actor.spells`. OpenMW vergibt dynamische Record-IDs; der Mod speichert deren Zuordnung im normalen Lua-Spielstand.

Die eigenen Texte und der eigene Mod-Code stehen unter der Projektlizenz MIT. Bestehende Spielmodelle, Symbole und Engine-Bestandteile werden hier nicht mitgeliefert oder umgelizenziert.
