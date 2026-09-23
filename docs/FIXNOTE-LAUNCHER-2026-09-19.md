# Startfehler im Genesis-Launcher behoben

**Fehler:** Beim Klick auf „Genesis spielen“ erschien `'NoneType' object has no attribute 'lower'`.

**Ursache:** Der gespeicherte frühere Spielprozess war bereits beendet. Die Windows-Abfrage `tasklist` lieferte dazu eine deutsche Meldung mit einem OEM-Zeichen. Python 3.14.6 versuchte im bisherigen `text=True`-Pfad, die Ausgabe als cp1252 zu lesen. Byte `0x81` löste im Lese-Thread einen `UnicodeDecodeError` aus; `stdout` blieb `None`. Anschließend scheiterte der direkte Aufruf von `.lower()`. Diese Abfolge wurde auf dem vorhandenen System mit einer ausschließlich lesenden Prozessabfrage reproduziert.

**Korrektur in `launcher.py`:** Die Abfrage bleibt jetzt im Byteformat. Für die Erkennung werden nur der ASCII-Prozessname `openmw.exe` und die genau gespeicherte Prozessnummer verglichen. Fehlende, leere oder fehlgeschlagene Abfrageergebnisse erzeugen eine verständliche Meldung und starten keinen weiteren Prozess. Fehler werden nicht pauschal verschluckt.

**Prüfung:** Der gezielte Nullwerttest reproduzierte vor der Korrektur denselben `AttributeError`. Danach bestanden alle **19 Unit-Tests**, darunter acht neue Launcherfälle: OEM-Meldung, `None`, leere Ausgabe, laufendes OpenMW, anderweitig wiederverwendete Prozessnummer, abweichende Prozessnummer, fehlgeschlagene Abfrage und erster Start. Prozessstarts sind in diesen Tests durch Dummies ersetzt.

```text
python -m unittest discover -s tests -v
```

Der tatsächlich verwendete `START.cmd` öffnet direkt die korrigierte `launcher.py` dieses Projektordners; eine weitere installierte Genesis-Kopie musste nicht geändert werden. Das eindeutig diesem Skript zugeordnete bisherige Launcherfenster wurde beendet und mit dem korrigierten Code wieder geöffnet. Der neue Launcherprozess läuft und antwortet. Dabei wurde kein Morrowind/OpenMW gestartet oder beendet und kein Spielstand verändert. Ein neuer echter Spielstart gehört nicht zu diesem Regressionstest. Das ältere Source-ZIP wurde durch diesen Patch nicht neu gebaut oder veröffentlicht.
