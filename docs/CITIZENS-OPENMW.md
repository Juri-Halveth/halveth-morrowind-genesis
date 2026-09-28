# Eigene Buerger in Morrowind (OpenMW 0.51)

Die Option **[Buerger +]** im F6-Weltlebenfenster ruft draussen zwei neue,
mod-eigene Bewohner: Liora vom Morgenweg und Tarin am Regenpfad. Sie folgen
zuerst einem kurzen nativen OpenMW-Wegpaket und erhalten danach ein
wiederholtes Wanderpaket mit einem Radius von 220 Spieleinheiten. Ein
unpassierbarer Anfangsweg wird nach 18 Sekunden beendet. Nahe beim Spieler
koennen sie in groesseren Abstaenden eine
kurze deutsche Textzeile zeigen. **[Buerger -]** entfernt genau diese beiden
Instanzen. Ist ihre Zelle gerade nicht geladen, merkt der Spielstand die
Entfernung vor und fuehrt sie beim naechsten Laden der Zelle aus.

Der Spieler muss diese Funktion selbst einschalten. Sie arbeitet im
Spielstand, benoetigt keinen separaten Browser und veraendert keine
Morrowind.esm-NPC-Datensaetze, Questvariablen oder AI-Pakete der Originalfiguren.
Der eigene Zustand und ausstehende Entfernungen werden mit dem OpenMW-Spielstand
gespeichert. Fremde oder ungueltige Zustandsdaten werden bewahrt und blockieren
weitere Eingriffe, statt andere Schauspieler zu treffen. Die erzeugten
Figuren sind auf zwei pro aktivem Spielstand begrenzt.

**Grenze:** Das ist kein autonomes Leben fuer jeden Original-NPC. OpenMW 0.51
stellt native AI-Pakete bereit, aber kein sicheres Eigentuemer-Tag fuer
bereits laufende Bethesda-Questpakete. Diese werden absichtlich nicht
ueberschrieben. Liora und Tarin sprechen aktuell durch seltene,
kontextgebundene Textzeilen; sie erhalten keine generierte Stimme, eigenen
Tagesplan, freie Questentscheidung oder dauerhafte Simulation ausserhalb der
geladenen Welt. Die gesonderte JARVIS-Unterhaltung bleibt davon unabhaengig.

Nativer Reproduktionstest auf einer **isolierten** OpenMW-Installation:

```powershell
python tests/integration_citizens.py
```

Der Test startet eine neue Wegwerf-Partie, lehnt die Mikrofon-Einwilligung
ausdruecklich ab, waehlt den vorhandenen Charakterursprung, ruft beide
Figuren, misst reale Bewegung, prueft fehlende geerbte Handelsdienste und
Lebenspunkte, entfernt sie ausser Sicht, speichert und laedt tatsaechlich und
prueft danach, dass die Original-NPCs noch in der Zelle sind. Er verwendet
keine persoenlichen Spielstaende. Ein bestandener Test belegt diesen Ablauf
in der getesteten Aussenzelle; er beweist weder alle Orte noch unbegrenzte
Simulationsdauer oder allgemeine Kompatibilitaet mit jedem Modpaket.

Technische Grundlage: [OpenMW-AI-Pakete](https://openmw.readthedocs.io/en/openmw-0.51.0/reference/lua-scripting/index_aipackages.html),
[Wanderpaket](https://openmw.readthedocs.io/en/openmw-0.51.0/reference/lua-scripting/ai/wander.html),
[Wegpaket](https://openmw.readthedocs.io/en/openmw-0.51.0/reference/lua-scripting/ai/travel.html),
[globale Welt-API](https://openmw.readthedocs.io/en/openmw-0.51.0/reference/lua-scripting/openmw_world.html)
und [NPC-Record-API](https://openmw.readthedocs.io/en/openmw-0.51.0/reference/lua-scripting/openmw_types.html).
