# Eigener Felsenhirsch 0.1.0 – begrenzter Kandidat

Eigene MIT-Geometrie, Skinning und Animationsdaten. Ein stilisierter Vierbeiner
mit 13 Gelenken, 2.440 Dreiecken und zehn Animationsgruppen. Git Bash ruft den
eigenen Python-Generator auf; OpenMW0.51 übernimmt die tatsächliche Animation.
Die CPU-Vorschau und die112 Prüfungen des serialisierten Modells sind eigene
Prüfstände. OpenMW0.51 hat im nativen Lauf das eigene Modell, Rendering- und
Kollisionstreffer sowie337,5 Spieleinheiten Bewegung in15 Simulationssekunden
geprüft. Der gesonderte Ladedurchlauf fand dieselbe gespeicherte Referenz genau
einmal und das Modul wieder deaktiviert. Diese15 nativen Assertions sind
keine Abnahme sämtlicher Animationen oder des grafischen Stils.

Das optionale Modul startet deaktiviert. Eine bewusste lokale Aktivierung über
`I.VeyraWildlife.setEnabled(true)` erlaubt höchstens eine eigene gespeicherte
Instanz in der eigenen Frontier. Die öffentliche Spieloberfläche erhält einen
Aktivierungsweg erst nach Runtimeprüfung. Dies ist kein Konsolen-Cheat-Befehl.
Die Normalproduktion enthält keine Probe-Registrierung.

Die Instanz verwendet einen lokal vorhandenen Creature-Record `mudcrab` als
Stats-/Enginevorlage, mit eigener Modellreferenz und eigenem Namen. Es werden
keine Bethesda-Modelle kopiert und keine Originalfiguren ersetzt. Die Figur
benötigt tatsächlich erfolgreich projizierte Navmesh-Wege. Native gemessene
Bewegung, sichtbare Animation und menschliche Stilabnahme bleiben getrennt.
Dead/Missing/Create-Hold führt zu keiner automatischen Ersatzinstanz.

Quellen der Schnittstellen: die gebundene lokale0.51-API und
[OpenMW0.51 COLLADA-Creature-Pipeline](https://raw.githubusercontent.com/OpenMW/openmw/openmw-0.51.0/docs/source/reference/modding/custom-models/pipeline-blender-collada-animated-creature.rst).
Das offizielle Exporterformat wurde als Referenz gelesen; Exportercode ist
nicht Bestandteil dieses eigenen Generators.

Noch offen: weitere Animationsgruppen im Spiel, eine normale Aktivierungs-
oberfläche und menschliche Bewertung. Die aktuellen Körper- und Gelenk-
übergänge bleiben eine sichtbare Prototypform. Die gespeicherte Prüfdatei
enthält eine Debug-Registrierung; nur der private Reload-Adapter ersetzt deren
Handler durch inerte Handler. Die Savebytes und Produktionsquellen bleiben
unverändert. Normalspielprofile enthalten diese Prüfadapter nicht.
