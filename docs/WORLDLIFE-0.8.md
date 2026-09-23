# Weltleben in Morrowind

Die Erweiterung `mod/scripts/halveth/worldlife.lua` läuft als PLAYER-Skript in
OpenMW 0.51. Sie beobachtet geladene NPCs im Umkreis von 3.000 Spieleinheiten
und speichert Figureninstanz, Namen, Beruf, Fraktionen, Ort, Begegnungstag und
echte Gespräche im Morrowind-Spielstand. Sichtungen werden pro NPC und Spieltag
einmal gezählt; wiederholtes Abfragen der Umgebung erzeugt keinen Fortschritt.
Bei einer späteren Sichtung wird eine Ortsänderung oder deutliche Bewegung
sichtbar. Das Fenster **Weltleben** ist im nativen Spielmenü erreichbar.

Der **regionale Fraktionsimpuls** ist eine neue Spielregel: Eine erste
Tagesbegegnung zählt einen Impuls, ein tatsächliches Gespräch zwei weitere.
Der Wert wird getrennt von den ursprünglichen Fraktionsdaten gespeichert.
Er beschreibt nur beobachtete Figuren und Gespräche in der geladenen Welt;
Aktivitäten außerhalb der geladenen Zellen werden nicht erfunden. Ein begrenzter
Auszug aus dieser Chronik kann dem lokalen Gesprächsbegleiter als Kontext
dienen. Die Simulation überschreibt keine originalen Queststufen, NPC-Skripte
oder Fraktionsränge.

Der Speichervertrag ist versioniert. Ungültige fremde Speicherdaten werden
nicht stillschweigend als leere Chronik überschrieben. Die Grenzen sind 128
Figuren und 96 Tagesimpulse; bei Erreichen bleibt der vorhandene Stand
erhalten und das Spiel zeigt einen Hinweis. Das UI und Speichern/Laden wurden
mit einem realen NPC in einer isolierten OpenMW-Sitzung getestet. Die Wirkung
auf beliebige Spielstände oder alle installierten Mod-Kombinationen ist damit
nicht nachgewiesen.

Ein erster **HALVETH-Wanderer** besitzt bereits tatsächliches Verhalten in
der Spielwelt. Die Knöpfe **Rufen**, **Pause**, **Weiter** und **Entfernen**
im Weltleben-Fenster steuern ausschließlich eine neu erzeugte NPC-Instanz.
Rufen ist nur draußen möglich; pro Spielstand wird höchstens eine Instanz
registriert. Das Skript startet ein natives OpenMW-Wanderpaket und prüft vor
Entfernen sowohl die Instanz- als auch ihre dynamisch erzeugte Record-ID.
Originale Quest- und Service-NPCs behalten ihre AI-Pakete. Ein isolierter
OpenMW-Test beobachtete 81,1 Welteinheiten tatsächliche Bewegung und prüfte
Pause/Fortsetzung, Save/Reload und Entfernen. Der Wanderer verwendet Körper-
und Kopfressourcen der vorhandenen Morrowind-Installation; er ist noch keine
globale NPC-Bevölkerungs- oder politische Vollsimulation.
