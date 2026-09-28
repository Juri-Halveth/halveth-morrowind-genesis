# NVIDIA App und Genesis

Genesis startet Morrowind über OpenMW. Für NVIDIA-Treibereinstellungen ist
`engine/openmw.exe` im ausgewählten Genesis-Installationsordner die rendernde
Anwendung. `HALVETH Morrowind.exe` bleibt der normale Spieleinstieg.

## Lokal hinzufügen

In NVIDIA App unter **Grafik → Programmeinstellungen** das Drei-Punkte-Menü
öffnen und das Programm manuell hinzufügen. Die tatsächliche `openmw.exe`
auswählen; anschließend prüfen, dass der Eintrag auf genau diese Installation
zeigt. Programmspezifische Einstellungen bleiben von globalen Einstellungen
getrennt. Eine Aufnahme in die lokale Programmliste bedeutet noch keine von
NVIDIA bereitgestellte automatische Optimierung.

NVIDIA beschreibt das manuelle Hinzufügen und die Suchordner in der
[offiziellen Einführung](https://www.nvidia.com/en-my/geforce/news/nvidia-app-download-and-features/).

## Spielaufnahme

**Alt+F9** startet oder beendet eine Aufnahme, **Alt+Z** öffnet das NVIDIA
Overlay. Den Aufnahmestatus im Overlay prüfen; ein ausgelöster Hotkey allein
beweist keine fertige Videodatei. Nach dem Stoppen in der Galerie kontrollieren,
dass der Clip nur das beabsichtigte Spielbild und die gewünschten Tonspuren enthält.
Eine Desktopaufnahme kann auch andere Fenster erfassen.

Quelle: [NVIDIA-Aufnahmefunktionen](https://www.nvidia.com/en-us/geforce/news/gfecnt/202411/nvidia-app-download-and-features/).

## Unterstützung durch NVIDIA

Das Feedback-Symbol oben rechts in NVIDIA App ist der offizielle Weg für einen
Funktionswunsch. Ein Bericht kann um Erkennung, ein Optimierungsprofil und eine
Klärung der unterstützten Overlay-Funktionen für OpenMW bitten. Ein eigenes
Hinzufügen, ein GitHub-Commit oder ein eingereichter Wunsch begründen weder eine
offizielle NVIDIA-Freigabe noch automatisch DLSS- oder Raytracing-Unterstützung.

Quelle: [NVIDIA-Feedbackweg](https://www.nvidia.com/en-us/geforce/news/gfecnt/20254/nvidia-app-update-g-assist-new-dlss-override-and-more/).

Die Spieländerung benötigt NVIDIA App nicht. Ein NVIDIA-Profil und eine
Aufnahme werden nicht durch diesen Quellpatch angelegt oder hochgeladen.
