# HALVETH Atmosphaere im laufenden Morrowind

`mod/shaders/halveth_atmosphere.omwfx` ist ein eigener OpenMW-Bildfilter. Die
Spielwelt, die Figuren und die vorhandenen Grafikpakete bleiben dieselben.
`mod/scripts/halveth/visuals.lua` aktiviert ausschliesslich diesen Filter und
stellt die native Schnittstelle `HALVETHVisuals` bereit:

- `getState()` meldet den gewaehlten Modus und ob OpenMW den Filter aktiviert hat.
- `cycle()` wechselt zwischen Scharlachlicht, Morgenrot, Lebendige Welt,
  Nachtglas und Original.
- `setMode('original')` deaktiviert den HALVETH-Filter. Andere Filter in der
  OpenMW-Kette werden dabei nicht beruehrt.

Die Auswahl wird im normalen OpenMW-Spielstand gespeichert. Ein vorhandener
Spielstand ohne HALVETH-Visualdaten startet mit Scharlachlicht; der
Originalmodus ist unmittelbar wiederherstellbar. Die Schnittstelle kann an
eine anklickbare Spieloberflaeche gebunden werden. F9 wird bewusst nicht belegt, weil es
in der verwendeten OpenMW-0.51-Eingabekonfiguration Quickload ausloest.

Der Shader liest die aktuelle Szene einmal und setzt einen sanften Ton in
Lichtern und Schatten sowie eine schwache Randabdunklung. Er erzeugt keine
zusaetzlichen Renderziele und laedt keine Texturen. Das begrenzt seinen
Zusatzaufwand, ersetzt aber keine gemessene Bildratenpruefung auf anderer
Hardware. Der Filter setzt die OpenMW-Nachbearbeitung voraus; wenn diese
deaktiviert oder der Shader nicht verfuegbar ist, zeigt `getState().enabled`
keine Aktivierung an.

Morgenrot ist eine eigene, kraeftigere HALVETH-Abstimmung mit waermerem Licht,
mehr Farbtiefe und Kontrast. Sie kopiert keine Grafik oder Shaderdatei aus
New World. Der Modus wirkt auf die laufende Morrowind-Szene, nicht auf die
Originaltexturen oder andere installierte Grafikpakete.

**Lebendige Welt** fragt in Aussenbereichen alle zwei Sekunden Sonnenanteil und
Sturmstatus der aktuellen OpenMW-Zelle ab und passt Waerme, Farbtiefe und
Kontrast innerhalb enger Grenzen an. In Innenraeumen bleibt der Filter bei
einer festen, milden Abstimmung. `getState().environment` zeigt die Quelle
`weather` oder `interior` sowie den zuletzt gelesenen Sonnenanteil. Die
Wetterabfrage veraendert weder Spielzeit noch Wetter oder Questdaten. Die
beiden Pfade wurden in frischen, isolierten OpenMW-0.51-Spielprozessen mit
aktiver Renderkette getestet. Das ist keine GPU-Benchmarkmessung.

Die Runtime-Anbindung basiert auf der zum installierten Engine-Tag gehoerenden
[OpenMW-0.51-Postprocessing-API](https://github.com/OpenMW/openmw/blob/openmw-0.51.0/files/lua_api/openmw/postprocessing.lua).
Die Wetterwerte stammen aus der
[OpenMW-0.51-Wetter-API](https://openmw.readthedocs.io/en/openmw-0.51.0/reference/lua-scripting/openmw_core.html#type-weather).
Der GLSL-Code und die Lichtprofile sind neu fuer HALVETH Genesis verfasst.
