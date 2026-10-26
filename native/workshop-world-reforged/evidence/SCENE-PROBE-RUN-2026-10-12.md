# World Reforged · begrenzte Szenenprobe · 2026-10-12

**Status:** `LOCAL_RUN_OBSERVED`
**Datenklasse:** `EXTERNAL_MINIMIZED`
**Scope:** ein separater lokaler World-Reforged-Kandidat mit frischer
Probe-Konfiguration unter `probes/<id>`.

Diese Kurzfassung beschreibt eine lokale Laufbeobachtung. Sie enthält weder
Spielinhalte, lokale Datenpfade, Spielstände noch den vollständigen Engine-Log.
Die ursprüngliche Workshop-EXE und das bestehende World-Reforged-Profil wurden
vor und nach dem Lauf hashgleich beobachtet.

## Gebundener Quell- und Werkzeugstand

- `Core.cs`: `5ac3a3471ca7bdda3820997278c965cad9e0c3fe5368a66ab63ba82fab1c8d9b`
- `Workshop.cs`: `7a2e79482b82efed16aad1d75e1b375a2f6cba18c9ac931ec71b6b9db0bb936b`
- separate Probe-EXE: `Morrowind-Workshop-WorldReforged-SceneProbe-v3.exe`
- Probe-EXE SHA-256:
  `95d7181a3971ebe8f3a77989fc877aca7d38a0551c16f4d466d40661506e6837`

Die Probe-EXE wurde neu neben der erhaltenen Kandidaten-EXE erstellt. Sie hat
weder die ursprüngliche Workshop-EXE noch das aktive Profil oder die lokale
OpenMW-Laufzeit überschrieben.

## Beobachtete Übergangskante

| Feld | Beobachtung |
| --- | --- |
| Start | `2026-10-12T19:14:00.9740085Z` |
| Menümarker | `MENU_INIT` beobachtet |
| Neuer-Spiel-Request | `NEW_GAME_REQUESTED` beobachtet |
| Szenenmarker | `SCENE_RUNNING` beobachtet um `2026-10-12T19:14:02.8203495Z` |
| Engine-Trace | `Starting a new game` und `Loading cell Imperial Prison Ship` beobachtet |
| Dwell | Controller wartete nach Szenenmarker mindestens 8 Sekunden; beobachtet: 8.0130654 s |
| Stop | `CONTROLLER_CLOSE_AFTER_SCENE_MARKER` um `2026-10-12T19:14:10.8334149Z` |
| Ende | Prozess beendet, Exit-Code `0`, kein Watchdog |

Die Engine meldete in dieser isolierten Probe außerdem, dass die Ressource
`video/new_game.webm` nicht geöffnet werden konnte. Diese eine Meldung bleibt
als konkrete Laufbeobachtung erhalten; aus ihr wird hier keine Ursache oder
Auswirkung außerhalb dieses Probelaufs abgeleitet.

## Aussagegrenze

Der Record zeigt einen gebundenen Übergang von Menü → neuer Spielstart →
Spieler-Erzeugung → kontrolliertem Prozessschluss innerhalb einer isolierten
lokalen Konfiguration. Er zeigt **keine** visuelle Abnahme, kein FPS-Ziel,
keine Kollisionsabdeckung, keine Save-Korrektheit und keine vollständige
Gameplay- oder Questprüfung.
