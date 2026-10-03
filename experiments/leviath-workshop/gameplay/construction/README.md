# LEVIATH Beetbau 0.1.3

Ein neuer eigener Bautyp fuer die lokale OpenMW-0.51/API129-Welt: ein
Pflanzbeet mit echtem Materialeinsatz, Saat, Spielzeit, Ernte und Rueckbau.
Die vorhandene Feldwerkstatt, der Courier und das Portal bleiben eigene
gebundene Module. Die Produktion enthaelt keine kostenlosen Materialinputs.

`F3` oeffnet das native Baumenue. `F6` ist in der vorhandenen Genesis bereits
fuer die Figur belegt; dieser Candidate aendert keine vorhandenen
Eingabedateien. Aktiviere dein wirkliches eigenes Beet, um genau dieses Beet
auszuwaehlen. Bau, Pflege, Ernte und Rueckbau brauchen den Spieler in
Reichweite. Die physische F3-Taste wurde nicht unabhaengig gedrueckt; die
normale native Spieler-UI und echte `activateBy(player)`-Ereignisse liefen.

Ein Beet kostet zwei `ingred_scrap_metal_01` aus dem wirklichen Inventar.
Die vorhandenen Referenzen werden in ein eigenes deaktiviertes Depot
bewegt; Menge, Record und Owner-Signatur werden danach beobachtet. Fuer
eine Saat werden zwei wirkliche `ingred_saltrice_01` separat eingelagert.
Nach 24 Spielstunden kann der Spieler einmal vier Saltrice ernten. Eine
spaete Ernte erzeugt denselben einmaligen Ertrag. Neue Ernten brauchen neue
Saat. Es gibt eine Materialtransaktion gleichzeitig; unklare Mengen oder
Referenzen bleiben HOLD und loesen keine Wiederholung aus.

Rueckbau bewegt die noch vorhandenen Rahmen und unverbrauchten Saat-
Referenzen ins Inventar zurueck. Er erzeugt keine Ersatzmaterialien.
Verbrauchte Saat wird nicht zurueckgegeben. Der Abschluss bindet den echten
Refundstand, die eigenen Referenzen mit Count0/disabled und eine reale
lokale World-Ray-Pruefung am bisherigen Beet. Erst dann wird genau dieses
Beet aus dem eigenen Register entfernt. Wiederholte Rueckbau-/Ernteaktionen
erzeugen keinen weiteren Ertrag.

Beete stehen nur in den 16 neuen Frontier-Zellen X64..67/Y-64..-61, maximal
32 pro Save. Der normale Spielerpfad prueft fuenf Bodenpunkte, Steigung,
Hoehenunterschied, Trockenheit, Kopffreiheit und die erreichbare Linie zum
Platz. Die globale Seite bindet Zelle, Position, Distanz und Abstand zu
den vorhandenen Beeten erneut. Das eigene COLLADA-Modell ist eine bewusst
einfache Bronze-/Boden-/Blattgeometrie mit 144 Dreiecken. Sein gruenes
Aussehen ist konstant; animierte Wachstumsstufen sind noch offen.

Die Frontier-ENTRY- und Plugin-Digests sind gebunden. Das normale eigene
Profil laedt den eingefrorenen Portal-Candidate fuer die Reise. Die optionale
Plaza war in diesen eigenstaendigen Construction-Proben nicht geladen.
Andere Bauplaene, Original-CELL-Overrides oder Gastserver gehoeren nicht
zum erreichten Stand.

```bash
bash CONSTRUCTION_BASH.sh stage
bash CONSTRUCTION_BASH.sh probe
bash CONSTRUCTION_BASH.sh reload-growing
bash CONSTRUCTION_BASH.sh reload-dismantled
bash CONSTRUCTION_BASH.sh cap-probe
bash CONSTRUCTION_BASH.sh reload-cap
bash CONSTRUCTION_BASH.sh play
```

`stage` wird einmal ausgefuehrt und ueberschreibt kein vorhandenes eigenes
Profil. `play` beginnt im normalen Engine-Menue; ein expliziter Save kann
mit `play --save "<vorhandener eigener Save.omwsave>"` geladen werden.
Es wird kein Verifikationssave ungefragt gestartet. Debugregistrations
werden nur fuer diese isolierten Proben oder fuer einen explizit gewaehlten
Save mit bereits gebundener Registration geladen. Deren OnLoad-Handler
stoppen das Seeden, Positionieren und die Kontrollfixture.

Am 03.10.2026 bestanden mit denselben fuenf 0.1.3-Produktionsdateien:

- Bau-/Farm-/Rueckbaulauf: 24 native PASS, Exit0. Kein Material -> kein Bau;
  realer Materialdebit; eigene Mesh-/Collisionbounds; keine ueberlappende
  Platzierung; native Beetaktivierung/Panel; echte Saat; 23 Stunden noch
  unreif; spaete Ernte nach 49 Stunden einmalig; Entfernung begrenzt;
  vier reale Ertraege; Saatverbrauch; erneute Saat aus realer Ernte;
  Refund/Rueckbau und wiederholte Aktionen ohne Duplikat.
- GROWING-Save: 5 native PASS, Exit0. Dieselben Beet-/Depot-IDs, echte
  zwei Rahmen und zwei Saat, verbleibende Spielzeit, kein Autoertrag.
- DISMANTLED-Save: 4 native PASS, Exit0. Kein wiedererzeugtes Beet und
  kein wiederholter Refund; Erntestand blieb erhalten.
- Cap-Test: 68 native PASS, Exit0, unter 90 Sekunden. 32 wirklich gebaute
  Beete mit jeweils zwei Materialien und eindeutigen IDs; der 33. Bau wurde
  trotz zwei vorhandener Materialien abgelehnt. Die 32 World-Refs blieben.
- Cap-Save: 5 native PASS, Exit0. Dieselben 32 Beet- und 32 Depot-IDs,
  alle Rahmenmaterialien, 32 lebende World-Refs, keine Inputwiederholung.

In jedem Lauf blieben alle 14 gebundenen Originaldateien unveraendert.
`FREEZE_CONSTRUCTION.json` bindet Produktionshashes und echte Receipts.
`evidence/probe-window-1.png` zeigt das visuell gepruefte native Baumenue;
`cap-probe-window-5.png` zeigt die tatsaechlich gerenderte eigene 4x8-
Beetanordnung. Diese lokalen QA-Bilder und Saves bleiben ausserhalb des
oeffentlichen Quellpakets.

Die Entwicklungsreceipts bleiben erhalten: fehlender `meshes`-Prefix,
eine zu enge Pfadgleichheit im Debugoracle und ein falsches
`isValid()==false`-Endoracle fuer Engine-Wrapper nach `remove()`.
Eine separate native Diagnose beobachtete wirkliche Count0/disabled-Refs
und die verschwundene World-Kollision. Der aktuelle SaveSchema2 bindet
Materialsignaturen und den RemovalWitness; alte Schema1-Entwicklungssaves
gehen laut Quellenpfad in LOAD_HOLD. Eine Migration wurde nicht getestet.

Offen bleiben normale physische F3-Bedienung, Owner-Signaturkonflikte in
einer eigenen nativen Probe, Saves mitten in Material-/Removaltransaktionen,
animiertes Wachstum und langfristiges Balancing. Native Mengenpruefungen
sind der begrenzte lokale Oracle fuer diese Zutaten; sie beweisen keine
externe Herkunft oder eine fremde Wirtschaft.

Eigene Lua-/Bash-/Python-/Dokumentations- und Geometriequellen sind MIT.
Morrowind-Originaldaten oder Originalmodelle werden nicht verteilt.
Die verwendeten API-Routen sind in der offiziellen
[OpenMW-Core-Dokumentation](https://openmw.readthedocs.io/en/openmw-0.51.0/reference/lua-scripting/openmw_core.html),
[World-Dokumentation](https://openmw.readthedocs.io/en/openmw-0.51.0/reference/lua-scripting/openmw_world.html)
und [Nearby-Dokumentation](https://openmw.readthedocs.io/en/openmw-0.51.0/reference/lua-scripting/openmw_nearby.html)
beschrieben. API-Beschreibung und die obigen tatsaechlichen Laufbelege bleiben
getrennte Quellen.
