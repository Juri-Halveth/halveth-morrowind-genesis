# Historischer Release-Entwurf – durch Morrowind 0.4 abgelöst

Dieser Plan vom 23. September 2026 dokumentiert eine frühere Produktentscheidung. Die eigenständigen Realms-/Portal-Garden-Projekte wurden eingestellt. Die aktive Entwicklung erfolgt innerhalb von TES III: Morrowind über OpenMW; die aktuelle Richtung steht in der README und in NATIVE-CONTENT.md. Die folgende frühere Planung ist keine aktuelle Zusage eines separaten Spiels, Unreal-Ports oder Steam-Releases.

Stand: 23. September 2026. Veröffentlichungsplan für den eigenen HALVETH-Code, eigene Inhalte und die nächste eigenständige Spielwelt. Dieser Plan beschreibt die Veröffentlichungsregeln und nächste Produktstufe; ein konkreter Upload, Unreal-Build oder Steam-Release erhält seinen eigenen Ergebnisnachweis.

## Veröffentlichung jetzt

Der öffentliche Quellstand soll maximale praktische Wiederverwendung erlauben: spielen, verändern, weitergeben, eigene Projekte bauen und kommerziell nutzen. Die vorhandene Morrowind-Erweiterung bleibt ein Adapter für eine separat installierte Spielkopie. Eine eigenständige HALVETH-Welt erhält eigene Orte, Geschichten, Figuren und Assets.

| Bestandteil | Veröffentlichung und Lizenz |
| --- | --- |
| Eigener HALVETH-Programmcode, Werkzeuge, Konfigurationen und Dokumentation | MIT. Copyright- und Lizenzhinweis bleiben in Kopien oder wesentlichen Teilen erhalten. Kommerzielle Nutzung und Weiterentwicklung sind erlaubt. [MIT-Original](https://opensource.org/license/mit) |
| Ausdrücklich aufgeführte eigene Originalgrafiken, beispielsweise das Scarlet-/LOVE-Textilmotiv | CC0-1.0, soweit eigene Rechte bestehen. Dateipfad und Herkunft werden in einem Asset-Verzeichnis gebunden. CC0 umfasst keine Marken- oder Patentrechte und klärt keine Rechte Dritter. [CC0-Original](https://creativecommons.org/publicdomain/zero/1.0/legalcode.en) |
| Externe Bibliotheken, Modelle, Mod-Pakete und Quellen | Ihre jeweiligen Lizenzen bleiben bestehen. Nur ausdrücklich zur Weitergabe zugelassene Dateien kommen in das Paket; sonst stehen dort Bezugs- und Installationsanleitungen. |
| Morrowind-Spieldaten, extrahierte Bücher/Dialogdatenbanken, persönliche Spielstände und private Laufzeitdaten | Bleiben außerhalb des öffentlichen Quellpakets. Der Adapter stellt sie auf dem eigenen Rechner über die dortige Installation bereit. |
| Unreal Engine, Editor und separat lizenzierte Epic-/Fab-Inhalte | Werden nicht unter HALVETH-MIT oder CC0 umgelabelt. Der öffentliche Quellbaum enthält den eigenen Projektcode und Installationshinweise. |

Die OpenAI-Europabedingungen ordnen Output im Verhältnis zwischen Nutzer und OpenAI dem Nutzer zu, soweit das Recht dies zulässt. Sie garantieren weder Einzigartigkeit noch automatisch Rechte an erkennbar fremden Inhalten. Deshalb erhält Originalkunst einen Herkunftseintrag, aber keine Behauptung exklusiven oder überall bestehenden Urheberrechts. [OpenAI Europe Terms, aktualisiert 16.01.2026](https://openai.com/policies/eu-terms-of-use/)

Spenden können freiwillig bleiben. Die MIT-/CC0-Freigabe selbst wird nicht von einer Zahlung, einem Wallet, einer Anmeldung oder einer späteren Zustimmung abhängig gemacht. Bezahlte Betreuung, Hosting und fertige Komfortpakete lassen sich daneben als eigene Leistungen anbieten.

Für neue Figuren werden eigene Namen, Erscheinungsbilder und Geschichten entwickelt. Marvel-spezifische Scarlet-Witch-/Loki-Darstellungen, Logos, Modelle und Filmdateien werden nicht als eigene freie Assets ausgegeben. Mythologische Inspiration und eigene Portal-/Magiegestaltung können den gestalterischen Ausgangspunkt bilden.

## Unreal als eigene nächste Spielstufe

Das Ziel ist ein eigenes Unreal-Projekt mit HALVETH-Weltgenerator, Portalübergängen, Magie, Gesprächen und speicherbaren Weltzuständen. Die vorhandene OpenMW-Erweiterung bleibt nutzbar. Eine Unreal-Projektdatei allein belegt noch keinen Engine-Port oder spielbaren Build.

Epic nennt MIT ausdrücklich als kompatible Lizenz. Eigener Projektcode kann offen bleiben, während Unreal selbst seiner EULA unterliegt. Engine-Quellen und Editor dürfen nicht als frei lizenzierter Bestandteil des öffentlichen HALVETH-Repositories erscheinen. Fertige Spiele dürfen Engine-Object-Code entsprechend der EULA als untrennbaren Bestandteil enthalten. OpenMW-/GPL-Engine-Code wird nicht in den Unreal-Quellbaum übernommen. [Epic: Unreal auf GitHub](https://www.unrealengine.com/ue-on-github), [Unreal-EULA, §§4–6](https://www.unrealengine.com/eula/unreal)

Vor einer kommerziellen Unreal-Veröffentlichung werden Release-Meldung, Credits, Produktbedingungen und erforderliche Drittanbieterhinweise umgesetzt. Die Standardregel sieht 5 % auf den definierten Royalty Revenue vor; die ersten 1 Mio. USD weltweiter Lebenszeit-Bruttoumsatz pro Produkt sind ausgenommen. Weitere Ausschlüsse und mögliche Sonderprogramme werden für den konkreten Release geprüft. Das ist keine pauschale Zusage dauerhafter Kostenfreiheit. [Unreal-EULA, Royalty Addendum](https://www.unrealengine.com/eula/unreal), [Epic: Game Deployment](https://www.unrealengine.com/release)

## Steam und spätere Blockchain-Ideen

Die Steam-Zielausgabe wird als vollständiges Spiel ohne Ausgabe oder Austausch von Kryptowährungen oder NFTs entworfen. Valve schließt derzeit Anwendungen aus, die auf Blockchain-Technologie aufbauen und solche Funktionen bereitstellen. Ein getrenntes zukünftiges Forschungsmodul ist deshalb keine zugesagte Steam-Funktion und kein Weg, diese Regel durch externe Links oder ausgelagerte Kontrollen zu umgehen. Eine andere konkrete Blockchain-Funktion benötigt eine eigene Policy-Prüfung. [Steamworks-Onboarding, Rules and Guidelines, Punkt 13](https://partner.steamgames.com/doc/gettingstarted/onboarding)

Für Steam werden später der Rechteinhaber, Bank-/Steuerangaben, Vertragsannahmen, App-Gebühr, Store-Seite und ein tatsächlich spielbarer Build benötigt. Aktuell nennt Valve 100 USD beziehungsweise den regionalen Gegenwert pro Produkt, für erste Titel eine Wartezeit von 30 Tagen nach Zahlung sowie mindestens zwei Wochen sichtbare Coming-soon-Seite. Zahlung, Identitätsprüfung und Verträge werden erst bei diesem konkreten Schritt erledigt. [Steamworks-Onboarding](https://partner.steamgames.com/doc/gettingstarted/onboarding)

Vorab erzeugte KI-Kunst und live erzeugte NPC-Texte werden im Content Survey wahrheitsgemäß angegeben. Für Live-Generierung beschreibt das Produkt die Begrenzungen gegen unzulässige Inhalte. Der Store zeigt tatsächliches Gameplay und bezeichnet Filmsequenzen entsprechend. Store-Seite und Build durchlaufen Valves Prüfung; ein GitHub-Release ersetzt diese Freigabe nicht. [Steam Content Survey](https://partner.steamgames.com/doc/gettingstarted/contentsurvey), [Steam Release Process](https://partner.steamgames.com/doc/store/releasing)

## Nächste umsetzbare Schritte

1. Öffentliches Exportverzeichnis aus einer expliziten Dateiliste erzeugen; eigenen Code, eigene Kunst und Abhängigkeiten zuordnen. `LICENSE` mit unverändertem MIT-Text, `LICENSES/CC0-1.0.txt` und ein dateibezogenes Asset-Verzeichnis beilegen. Für CC0 ist der [offizielle Klartext](https://creativecommons.org/publicdomain/zero/1.0/legalcode.txt) verfügbar.
2. Installation, Rückwechsel und Tests dokumentieren; private Laufzeitverzeichnisse, extrahierte Spieldaten und Engine-Verzeichnisse aus Export und Git ausschließen. Öffentliches Paket und Commit erst nach tatsächlicher Erstellung mit Hash und Versionsnummer erfassen.
3. Eine eigene kleine Unreal-Szene bauen: ein begehbarer Ort, ein Portal, ein eigener Charakter, ein Zauber und ein Speichervorgang. Versionsbindung, Performance und Paketierung am installierten Editor prüfen.
4. Danach Weltenanzahl, Dialoggedächtnis, Mehrspielerbetrieb und Gestaltung erweitern. Aus stabilen Builds entsteht der Steam-Kandidat; Onboarding und kommerzielle Veröffentlichung folgen als eigene konkrete Schritte.

## Quellenstand und Reichweite

Recherche am 23.09.2026 mit Exa: drei Suchläufe mit insgesamt 15 angeforderten Trefferzeilen; zehn offizielle URLs direkt abgerufen, darunter zwei Darstellungen desselben CC0-Dokuments. Verwendet wurden Primärquellen von Open Source Initiative, Creative Commons, OpenAI, Epic Games und Valve. Suchanzeigen und Drittanbieter-Zusammenfassungen tragen keine Entscheidung. Die Quellen regeln ihre jeweiligen Plattformen und Verträge; sie beweisen weder eine bereits erfolgte Veröffentlichung noch Rechte an ungeprüften Einzeldateien. Vor einem späteren Store-Release wird der dann aktuelle Regelstand erneut gebunden.
