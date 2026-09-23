# Vivec, gekaufte Urkunde und 250 Gold

Stand: 2026-09-19. Recherche für das Bewahren einer persönlichen Einzelspieler-Erinnerung. Das Spiel, die Masterdateien und Spielstände wurden hierfür nicht verändert.

**Der erinnerte Vorgang ist noch nicht eindeutig zugeordnet.** Die Kombination aus Vivec, einem Kauf statt Diebstahl und wiederholt 250 Gold lässt sich durch keinen der geprüften Kandidaten vollständig verbinden. Die Erinnerung bleibt als eigener offener Eintrag erhalten; diese Notiz ersetzt sie nicht durch eine Vermutung.

| Kandidat | Was passt | Was offen bleibt oder abweicht |
|---|---|---|
| **Chronicles of Nchuleft / Edwinna Elbert** (`MG_NchuleftBook`) | Exakt 250 Gold als Vorschuss. Das gesuchte Buch lässt sich bei Jobasha in Vivec kaufen. Im lokalen Dialog werden sowohl Buchhändler als auch Vivec ausdrücklich genannt. | Es ist ein Buch, keine Grundstücksurkunde. Edwinna ist die Auftraggeberin außerhalb Vivecs. Eine wiederholte Auszahlung wurde nicht beobachtet. |
| **Rethan Manor Land Deed / Baren Alen** (`HH_Stronghold`) | Grundstücksurkunde in Vivec; Baren Alen bietet sie ausdrücklich per Handel an. Ein historisches Patch-Changelog beschreibt, dass sein Urkundendialog nach dem Kauf bestehen blieb. | Dieser konkrete Kaufdialog enthält keine Goldauszahlung. Ein fortbestehendes Thema ist für sich noch kein 250-Gold-Glitch. |
| **Brallion’s Ring / Gentleman Jim Stacey / Ilmeni Dren** (`TG_SS_GreedySlaver`) | Ein als Diebstahl formulierter Auftrag kann durch Ringkauf gelöst werden. Ziel ist Ilmeni Dren in Vivec; das Geld aus dem Ring dient in der Geschichte befreiten Sklaven. | Kauf bei Brallion in Sadrith Mora; lokale Kaufdialoge ziehen 500 beziehungsweise 800 Gold ab. Die geprüften Abschlussdialoge bei Ilmeni und Stacey zahlen keine 250 Gold. |
| **Forged Land Deed / Indrele Rathryon** (`TG_SS_Generosity2`) | Gefälschte Urkunde aus der Bibliothek in Vivec; Grundstücksrechte und Hilfe für eine betroffene Person sind zentrale Themen. | Übergabe an Indrele in Seyda Neen. Die geprüften Übergabe- und Abschlussdialoge enthalten keine 250-Gold-Auszahlung und keinen entsprechenden Kaufweg. |
| **The Bad Actor / Miun-Gei** (`EB_Actor`) | Exakt 250 Gold im Vivec-Dialog `annoying fool`. | Der gefundene Zweig bezieht sich auf den Tod Marcel Maurards; kein Urkunden- oder Ringkauf. Daher kein guter inhaltlicher Treffer für die erinnerte friedliche Lösung. |
| **Juicedaw Feather Ring / Lorbumol gro-Aglakh** (`FG_DebtOrc`) | Ringbeschaffung in Vivec und eine Alternative zum Töten sind vorhanden. | Der lokale Belohnungsdialog gibt 100 Gold; kein passender 250-Betrag. |

## Lokale Primärbelege

Ausgangspunkt ist die tatsächlich eingelesene englische `Morrowind.esm`, SHA-256:

`5c3c8c2cbd20e25901b59b3ece33d36b7ef0e3d60ad8d11828bcc61a5ead1647`

Die vorhandenen Funktionen `records`, `text` und `from_config` aus `scripts/import_lore.py` wurden zum lesenden Durchlaufen der aktiven Master-/Pluginliste genutzt. Es wurden Dialogtexte und gespeicherte Resultscripts betrachtet, keine Scripts ausgeführt.

- `Chronicles of Nchuleft`, INFO `1786816122756313471`, Akteur `edwinna elbert`: Resultscript enthält die Zuteilung von genau 250 Gold und Journalfortschritt auf Stufe 10. INFO `16493505187536318` verweist später auf das bereits gegebene Geld; INFO `26081231041180118731` ist Jobashas Buchhinweis. Das belegt den Vorschuss und den Buchkandidaten, nicht seine beliebige Wiederholbarkeit.
- `land deed`, INFO `23593135496072781`, Akteur `baren alen`: Handelsangebot für die Urkunde des verlassenen Rethan Manor; Resultscript leer.
- `Brallion’s Ring`, INFO `7945315681663820847` und `714323452207912987`, Akteur `brallion`: Kaufzweige über 500 beziehungsweise 800 Gold und Ringtransfer. INFO `1490827291559923344` bei Stacey beendet den Auftrag mit Gildenansehen und Sympathie, ohne Goldtransfer.
- `forged land deed`, INFO `111723425101266659` bei Stacey: Abschluss mit Gildenansehen und Sympathie, ohne Goldtransfer. Die geprüften Übergaben an Indrele entfernen die Urkunde und verändern teilweise Sympathie, ohne 250 Gold zu geben.
- `annoying fool`, INFO `29324731118607449`, Akteur `miun_gei`: 250 Gold und Journalstufe 90; der Antworttext bezieht sich ausdrücklich auf Marcel Maurards Tod.
- `Juicedaw Feather Ring`, INFO `24130260953192126206`, Akteur `lorbumol gro-aglakh`: 100 Gold, Ringübergabe und Journalstufe 100.

Die gezielte Suche nach direkten 250-Gold-Zuteilungen in den Dialog-Resultscripts der Basismasterdatei fand sieben Einträge zu sechs Themen: `Chronicles of Nchuleft`, `Felen Maryon’s staff`, `Dissapla Mine`, `annoying fool`, zweimal `Dura gra-Bol` und `Vas`. Die weiteren 250-Gold-Treffer der eingelesenen Erweiterungen betreffen unter anderem Mournhold und erklären die Urkunden-Erinnerung nicht unmittelbar. Es wurden auch die aktiven Erweiterungs-/Plugin-Dateien nach entsprechenden Resultscript-Zeilen durchsucht.

Diese Abdeckung umfasst gespeicherte Dialogeinträge und ihre Resultscript-Texte. Allgemeine `SCPT`-Programme, damalige Spielversionen, nicht geladene Mods, früher entfernte Patches und der historische Spielstand sind damit nicht vollständig untersucht. Dialogbedingungen wurden nicht im Spiel ausgewertet. Wiederholbarkeit bleibt offen.

## Ergänzende Webquellen

Der historische Patchautor dokumentiert für Baren Alen eine Korrektur, die sein Urkundenthema nach dem Kauf ausblendet; das ist ein konkreter Hinweis auf einen wiederholten **Dialog**, ohne dort einen 250-Gold-Transfer zu belegen. [Unofficial Morrowind Patch – Quest/Bug Fixes](https://paulcarr.com.au/elderscrolls/patch/quest.htm)

Eine Spielerfrage zum Nchuleft-Buch beschreibt genau die Entscheidung zwischen Diebstahl in der Vivec-Bibliothek und Kauf bei Jobasha. Dieser sekundäre Hinweis passt zu den lokalen Buchdialogen, dokumentiert aber ebenfalls keine wiederholten Auszahlungen. [GameFAQs – How do I get the Chronicles of Nchuleft?](https://gamefaqs.gamespot.com/xbox/480241-the-elder-scrolls-iii-morrowind/answers/216956-how-do-i-get-the-chronicles-of-nchuleft)

Ein älterer Questbericht nennt den Kauf von Brallions Ring als Alternative zum Diebstahl und die Übergabe in Vivec. Die lokalen Resultscripts liefern hier die belastbarere Angabe zu den Kaufbeträgen. [Neoseeker – Gentleman Jim Stacey Quests](https://www.neoseeker.com/forums/3222/t342317-need-help-with-gentleman-jim-stacey-quests/)

Direktabrufe der UESP-Seiten zu Brallions Ring und Chronicles of Nchuleft waren in diesem Durchlauf nicht zugänglich. Aus diesem Zugriffsproblem wird keine inhaltliche Aussage abgeleitet.

## Nächster konkreter Anknüpfungspunkt

Ein erinnerter NPC-Name, die Farbe/Form des Gegenstands, ein Dialogwort oder ein alter Screenshot kann die Kandidaten rasch trennen: **Buch und Jobasha**, **Urkunde und Baren Alen**, **Ring und Ilmeni Dren** oder **Schauspieler und Miun-Gei**. Bis dahin bleiben alle genannten Kandidaten erhalten. Es wurde kein passender Originaldialog umgebaut und kein angeblicher Glitch nachgebildet.
