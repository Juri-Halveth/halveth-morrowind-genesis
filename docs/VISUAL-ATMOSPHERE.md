# HALVETH Atmosphaere im laufenden Morrowind

`mod/shaders/halveth_atmosphere.omwfx` ist ein eigener OpenMW-Bildfilter. Die
Spielwelt, die Figuren und die vorhandenen Grafikpakete bleiben dieselben.
`mod/scripts/halveth/visuals.lua` aktiviert ausschliesslich diesen Filter und
stellt die native Schnittstelle `HALVETHVisuals` bereit:

- `getState()` meldet den gewaehlten Modus und ob OpenMW den Filter aktiviert hat.
- `cycle()` wechselt zwischen Scharlachlicht, Nachtglas und Original.
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

Die Runtime-Anbindung basiert auf der zum installierten Engine-Tag gehoerenden
[OpenMW-0.51-Postprocessing-API](https://github.com/OpenMW/openmw/blob/openmw-0.51.0/files/lua_api/openmw/postprocessing.lua).
Der GLSL-Code und die Lichtprofile sind neu fuer HALVETH Genesis verfasst.
