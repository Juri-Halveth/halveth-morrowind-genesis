ENTITY LIFE 0.1.0 -- IDENTITAET, WANDEL UND BEZIEHUNGEN

Eine ID adressiert eine Entitaet. Ihr Aussehen gehoert zum veraenderlichen
Zustand; dessen SHA-256 ist ein anderer Wert. Erfundenen Namen kann man aendern,
ohne die ID zu aendern. Ein Hash beweist weder Leben noch Bewusstsein.

Der lokale Katalog liest die explizit gebundenen TES3-Quelldateien und vergibt
IDs an logische Records und platzierte FRMR-Instanzadressen. Zwei Kopien derselben
Tasse haben getrennte Instanz-IDs und einen gemeinsamen Template-Verweis.
Eigene Dateien koennen unter einem separaten Namensraum hinzukommen.

Die Ausgabe ist ein komprimierter lokaler Datenkatalog, kein neues Spiel und
keine Aufnahme aller Menschen oder Gegenstaende der realen Welt. Die Zuordnung
echter Menschen ist ein eigener, hier nicht implementierter Auftrag.

SEMANTIC_ADDRESS bindet bekannte Record-Schluessel. SOURCE_REFERENCE_OWNER_AND_INDEX
bindet urspruengliche Plugin-Adresse und Referenznummer, unabhaengig von Position
und Aussehen. SNAPSHOT_ADDRESS markiert unbekannte semantische Schluessel;
hier gilt die Adresse nur fuer den gebundenen Quellstand.
Verschobene CELL-Referenzen, Spielstandobjekte und erst zur Laufzeit erzeugte
Gegenstaende brauchen einen eigenen nativen Adapter. Luecken stehen im Receipt.

Git Bash:
  bash ENTITY_LIFE.sh demo connected bright
  bash ENTITY_LIFE.sh demo visual-only contemplative
  bash ENTITY_LIFE.sh find --registry ../entity-life-catalogue-0.1.0/registry.jsonl.gz --query goblet

Katalog aus eigenen lizenzierten Daten neu erzeugen:
  bash ENTITY_LIFE.sh catalogue --config /path/openmw.cfg --output /path/FRESH \
    --assets /path/OWN-ASSETS
ENTITY_PYTHON kann auf einen vorhandenen Python-Interpreter zeigen.
ENTITY_REGISTRY_DIR kann eine separat gespeicherte Katalogausgabe adressieren.

Die Entscheidungslogik der Demo ist echtes Bash. Sie waehlt aus einer offen
genannten endlichen Grammatik Haare, Praesentation und Farbparameter. Der
Spielerimpuls ist eine ausdrueckliche Eingabe, keine gemessene biologische Energie.
Die drei Kategorien beschreiben eine Spielpraesentation, keine Definition von
Geschlecht oder persoenlicher Identitaet.

CONNECTED verknuepft die Auswahl ueber erfundene Geruecht- und Gesellschaftsregeln
mit einem Dagoth-Endpunkt. VISUAL-ONLY fuehrt dieselbe Art von Darstellungsauswahl
ohne diese Story-Regeln aus. Das sind deklarierte neue Designregeln; sie werden
nicht aus den Originalrecords abgeleitet. Das append-only TSV-Journal verkettet
die Demo-Ereignisse mit SHA-256, liefert aber keine Herkunftsauthentisierung.

Der Katalog und die Bash-Demo veraendern keine Engine, Quests, Originaldaten,
Menschen oder Spielstaende. Echte dynamische Figuren und verzweigte Quests im
laufenden Spiel benoetigen Modell-, Animations-, Dialog- und Speicheradapter.
Der bereits gepruefte REZERO-Spielstart bleibt als gesunder Elternstand erhalten.

FRAGMENT_UNIVERSE.sh gibt einem eigenen kleinen Datenfragment einen separaten
Namensraum mit Elternbindung, veraenderlichem Zustand und einem typisierten
Rueckgabeereignis. Ungueltige Kandidaten werden erhalten und nicht uebernommen.
Die Demo erzeugt eine ungecommitete Anforderung; der Elternzustand bleibt exakt
gleich. Das ist ein endliches Softwaremodell, keine physische Universumswirkung.

Eigener Code: MIT. Keine Bethesda-Daten, privaten Kataloge oder Originalbeweise
werden mit dem oeffentlichen Quellcode verteilt.
