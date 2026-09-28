# Leuchtende Orte

Eine optionale Begegnung in derselben Morrowind-Welt: Der Spieler sieht einen
Kristall oder Baum der lokal installierten LUCINET-World-Reforged-Schicht an.
In der vorhandenen F8-Schreibkonsole lauscht `/resonanz` diesem Ort;
`/resonanz antworten` gibt ihm einen Gruß zurück. Die Konsole schließt sich,
damit der kurze Lichtkreis im Spiel sichtbar ist. `/resonanz status` liest die
letzte Antwort in derselben Konsole. Es gibt keine zusätzliche Startfrage.

## Verhalten

- Die erste Begegnung beginnt mit Lauschen. Ein Gruß vor dem Lauschen verändert nichts.
- Ein späterer Gruß erreicht Stufe 2. Ein erneutes Lauschen an einem späteren
  Spieltag erreicht Stufe 3. Wiederholte Grüße ersetzen diesen Tageswechsel nicht.
- Jede konkrete Pflanzeninstanz hat eine eigene Erinnerung, auch wenn mehrere
  Pflanzen denselben Grafikdatensatz verwenden. Der normale Spielstand speichert
  bis zu 128 Orte. Ein volles Buch überschreibt keine alten Orte.
- Die Antworten sind eigene deutsche Spieltexte. Tageslicht und Sturm können
  eine Antwort färben. Es gibt keine zufällig vergebenen Fertigkeiten, Zauber
  oder Gegenstände und keine Änderung an vorhandenen Quests.
- Ein kurzer nativer Magieeffekt steht am tatsächlichen sichtbaren Trefferpunkt.
  Der Effekt verwendet ein in den eigenen Morrowind-Daten gefundenes Modell;
  er wirkt rein optisch und führt keinen Schadens- oder Heilzauber aus.
- Der Effekt wird spätestens nach vier Simulationssekunden oder beim Zellwechsel
  entfernt. Eine Pause hält auch die Simulation an. Die sechs Sekunden
  Wiederholungsbegrenzung werden im Save erhalten.
- Der Gesprächsbegleiter erhält die letzte erfolgreiche Begegnung als
  `authored_plant_resonance`. Das ist eigener Spielinhalt, keine Originalbiografie.

## Voraussetzungen und Erhalt

Die fünf unterstützten Modellpfade sind `meshes/lucinet/plant0.dae`,
`plant1.dae`, `tree0.dae`, `tree1.dae` und `tree2.dae`. Die Reforged-Grafikschicht
ist ein vorhandener lokaler Zusatz und wird durch diesen Quellpatch nicht
heruntergeladen oder mitveröffentlicht. Ohne diese Modelle bleiben die übrigen
Spielfunktionen verfügbar; ein Resonanzversuch meldet das fehlende passende Ziel.

Die Modelle und ihre Materialien selbst bleiben erhalten. Ihre eingebetteten
Animatorspuren werden nicht umgeschrieben; der neue Effekt wird durch die
OpenMW-Welt-VFX-Funktion hinzugefügt. Das ist ein zusätzlicher sichtbarer
Spielmechanismus und keine vollständige Animation jeder Baumkrone.

Unbekannte Speicherformate bleiben unverändert im Save erhalten; die Erweiterung
meldet in diesem Fall einen blockierten Zustand. Der alte Inhalt wird nicht durch
ein neues leeres Gedächtnis ersetzt. Original- und persönliche Save-Dateien werden
vom Installationspatch nicht bearbeitet.

## Prüfung und Installation

`tests/integration_resonance.py` verwendet eine wegwerfbare native Spielsitzung
mit eigenen Testobjekten. Die Grafikpfade werden aus einer vorhandenen eigenen
Installation gelesen. Persönliche Spielstände sind keine Testeingabe.

`scripts/Apply-WorldResonance.ps1` zeigt standardmäßig den Plan. `-Apply` kopiert
die sechs eigenen Laufzeitdateien in eine vorhandene Genesis-1.0.6-Installation,
prüft Ausgangshashes und hält die Originaldateien samt Installationsmanifest als
Rückkehrpunkt fest. Bei laufender installierter Engine oder Begleiter stoppt der
Patch. Der bestehende Spieleinstieg und die vorhandene EXE bleiben der Einstieg.

Native Testergebnisse sind gesonderte Belege. Ein Quellcommit oder ein
Dateivergleich allein bestätigt weder optische Qualität noch alle Spielsituationen.

Am 28.09.2026 bestanden 104 Quelltests mit einem übersprungenen Windows-Symlinktest.
Der native Test bestand mit der installierten OpenMW-Engine und dem vorhandenen
Genesis-Profil: F8-Befehlsweg, tatsächlicher Sichtstrahl, zwei getrennte Instanzen,
Speichern/Laden einschließlich Restwartezeit, Wiedersehen am Folgetag und
Effektabbau. Der F8-Befehlsweg wurde über das vorhandene Testereignis ausgelöst;
dies ist kein Nachweis einer physischen Tastatureingabe. Die grün-goldene
Lichtantwort wurde zusätzlich im nativen Fenster gesehen.

Der Test prüft keine vollständige Landschaftsabdeckung. Randfälle wie das
129. gemerkte Objekt, beschädigte Save-Payloads und Zellwechsel mitten im Effekt
sind durch Regeln begrenzt, aber im genannten nativen Durchlauf nicht ausgeübt.

## API-Grundlage

- [OpenMW Rendering-Ray](https://openmw.readthedocs.io/en/latest/reference/lua-scripting/openmw_nearby.html)
- [OpenMW Welt-VFX](https://openmw.readthedocs.io/en/latest/reference/lua-scripting/openmw_world.html)
- [OpenMW statische Datensätze](https://openmw.readthedocs.io/en/latest/reference/lua-scripting/openmw_types.html)

Die tatsächlich installierten API-Dateien werden für die lokale Laufzeit zusätzlich
mitgelesen. Dokumentation einer neueren Engine ersetzt den nativen Test nicht.
