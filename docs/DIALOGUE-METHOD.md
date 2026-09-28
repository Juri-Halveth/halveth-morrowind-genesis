# Gesprächsmethode und native Antwortanzeige

Die bestehende F8-Konsole zeigt **Bereit**, **Anfrage gesendet · Antwort ausstehend**,
**Antwort eingetroffen**, **Lokales Modell nicht erreichbar** oder **Antwort
fehlgeschlagen**. Diese Texte wechseln durch tatsächliches Absenden, passende
Mailbox-Antworten und das vorhandene Zeitlimit. Die Anzeige bleibt statisch und
lesbar; es gibt keinen zusätzlichen Browser, kein Dauer-Redraw und kein neues
Fenster am Spielbeginn.

Das kleine Modul `dialogue_method.py` bindet die Methode
`hypothesis-revision-cycle.v1`, Version **1.0.0**, an den vorhandenen lokalen
JARVIS-/NPC-Prompt. Fragen mit einem Prüf-, Ursachen-, Vergleichs- oder
Vorhersagehinweis erhalten die kompakte Leitlinie: Hypothese, Gegenmodell,
unterscheidende Beobachtung, vorher benannte Minimum-Evidenz, Änderungsbedingung
und belegtes Ergebnis mit offenem Rest. Die Auswahl ist eine Sprachheuristik,
keine Tatsachen- oder Autoritätsentscheidung.

Begrüßungen und gewöhnliche Gespräche erhalten keine Prüfliste. Der Prompt
fordert NPCs auf, in ihrer Rolle, ihrem Wortschatz und ihrem belegten
Wissensrahmen zu bleiben. Er verlangt auch die Trennung früherer Ereignisse,
aktueller Beobachtung und bedingter Zukunftsvorhersage. Das sind
Antwortvorgaben; sie garantieren keine fehlerfreie Modellausgabe. Ein alter
Gesprächssatz wird dadurch weder zu einer ausgeführten Spielaktion noch zu
einem neuen Weltbeleg.

Die Ausgabe des Sprachmodells bleibt Prosa. Die bestehenden getypten
Spielaktionen, ausdrücklichen Auslösungen und Welt-Receipts bleiben zuständig
für tatsächliche Änderungen. Die Methode vergibt keine zusätzlichen Rechte.

Der Clip zu **Thinking Orbs** inspirierte eine deutliche Zustandsanzeige. Hier
wurde eigener nativer OpenMW-Textcode verwendet; es wurden weder npm-Pakete
noch Code, Bilder oder Lizenzbehauptungen aus dem Clip übernommen. Eine
eingetroffene Antwort besagt nur, dass Text angekommen ist, nicht dass ihr
Inhalt nachgewiesen wurde.

Die neue Begleiterdatei ist in der Positivliste des Quellpakets und dessen
Pflichtdateien enthalten. Ein vorhandener Installer kann sie dadurch beim
nächsten regulären Build aufnehmen. Diese Quelländerung ist selbst noch kein
installiertes Update oder veröffentlichtes Release.
