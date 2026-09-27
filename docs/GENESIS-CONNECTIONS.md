# Genesis-Verbindungen: beobachteter Rechner, tatsächlicher Spielpfad

Ein Port ist eine lokale Transportadresse, kein eigenes Universum und keine automatisch bestehende Verbindung. Dieses Blatt trennt **Quellkonfiguration**, **laufenden Listener** und **belegte Datenübergabe**. Der punktuelle Windows-TCP-Snapshot vom 27.09.2026 gegen 18:10 UTC bezog sich auf den eigenen Rechner. Er ist keine Dauermessung, kein Paketmitschnitt und keine Aussage über fremde Netze.

| Port | Aktueller lokaler Dienst im Snapshot | Zweck im geprüften Code | Genesis-Anbindung |
| ---: | --- | --- | --- |
| `18765` | `127.0.0.1`, Genesis-Companion `server.py` | Lokale Status-, Gesprächs- und Aktions-API | Der sichtbare Spieleinstieg startet ihn; die native Spielmod tauscht Ereignisse vor allem über Logzeilen und eine VFS-Datei aus. |
| `11434` | Ollama auf `[::]` | Lokale Modell-API; Genesis adressiert `127.0.0.1:11434` und das Modell `hermes3:8b` | Modellantworten für freie Gespräche; das Spiel startet auch ohne Modell. Externe Erreichbarkeit der Wildcard-Bindung wurde nicht geprüft. |
| `32145` | LUCINET auf `127.0.0.1` | LUCINET-Oberfläche und Agent-Command-Route | Im geprüften Genesis-Code kein direkter Aufruf gefunden; ein Listener allein verbindet beide Anwendungen nicht. |
| `8766` | LUCINET Local Jarvis auf `127.0.0.1` | Eigene lokale `/ask`- und `/health`-Routen | Im geprüften Genesis-Code kein direkter Aufruf gefunden. |

`32147` ist in LUCINET als optionaler Proxy-Port definiert und `18766` erscheint als Genesis-Testport. Auf beiden wurde im selben kurzen Snapshot kein Listener gesehen. Andere PC-Listener gehören nicht schon wegen ihres Ports zum Spiel.

Die tatsächlich belegte Spielkette ist: OpenMW-Lua schreibt getypte `HALVETH_FRAME`-Ereignisse ins Spiel-Log; der lokale Companion liest diese Zeilen, fragt bei Bedarf Ollama und legt eine strukturierte Antwort in `mod/bridge/inbox.json`; die OpenMW-Lua-Mod liest die Antwort über das virtuelle Dateisystem. Die native F6/F7/F8-Oberfläche, Bücher, Wetterreaktionen und der Portalfilm laufen in OpenMW. Für eine künftige direkte LUCINET-Brücke braucht es einen eigenen, versionierten Adapter und einen Test von Datentyp, Zustimmung, Eingabegrenze, Antwort und Spielwirkung. Ein offener Port ersetzt keinen solchen Adapter.
