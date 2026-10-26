# LEVIATH Frontier Scenery 0.1.0

Ein separat gebauter eigener Waldkandidat in genau einer eigenen Außenzelle: (65,-62). 20 Referenzen der eingefrorenen dichten Krone, 20 neue kleine Steingruppen und 28 neue Grasgruppen. 68 Referenzen innerhalb eines Budgets von 128. Keine bestehende Baumklasse und keine Original-Spielzelle wird überschrieben; keine LAND-, Wetter-, Portal-, NPC-, Musik- oder Profiländerung.

Diese Einheit ist nach statischer Byte-/Geometrie-/Boden-/Korridorprüfung reviewbar. Rendering, Stammkontakt, Kronenüberhang, echte Kollision, Wegbegehbarkeit, Navigation und Framezeiten brauchen die getrennte Root-Engineprobe. Der Koordinatenplan und mathematische Dreiecksumfang sind keine native Optik- oder Performanceabnahme.

## Additive Integration

Abhängigkeiten in dieser Reihenfolge: eingefrorene Frontier, eigene Texturvariante, dichte Krone, dann diese Einheit. Sie benötigt die Crown-STAT `veyra_swamp_crown_01`. Die beiden eigenen neuen STAT-IDs heißen `veyra_frontier_stone_cluster_01` und `veyra_frontier_grass_01`.

```text
data="<presentation-candidate>/frontier-scenery-candidate/mod"
content=LEVIATH-Frontier-Scenery.esp
```

Die ESP bindet genau `Morrowind.esm`, `LEVIATH-Frontier.esp` und `Veyra-Dense-Crown.esp` mit exakten Größen. Sie ergänzt 68 eigene FRMRs 0x501..0x544 in einem identischen Header der eigenen Frontier-Zelle. Die beiden eigenen kleinen Modelle brauchen vorhandene eigene `textures/veyra/frontier/frontier_stone.dds` und `textures/veyra/crown_leaf_01.dds`; keine Textur ist hier dupliziert. Alle Abhängigkeiten samt Digests stehen im Manifest.

## Gelände und freie Spielbereiche

Seed 2026100368. Jede tatsächliche gespeicherte XY-Position liegt auf einem 128er LAND-Vertex, jedes Z kommt aus einem zweiten Decoder des eingefrorenen VHGT. Der Pfad hat fünf Kontrollpunkte, zentrale Höhe 320 und Halbbreite 600 plus die tatsächliche niedrige Modellhülle und 128 Einheiten Zusatzabstand. Die vollständigen Float32-Positionen, Referenzen, Rotationen, Skalierungen und VHGT-Vertex-/Payload-Proofs stehen in SCENERY_MANIFEST.json.

Die niedrige Kronenhülle stammt aus der serialisierten eigenen DAE: radial höchstens 210.94 Einheiten unter lokal Z400; maximale XY-Kronenhülle 1163.13. Die Prüfung berücksichtigt die Instanzskalierung. Für Stein/Gras wird die tatsächliche Geometriehülle vor der Platzierung berechnet und konservativ für maximale Skalierung plus 16 Einheiten reserviert. Gras steht nur auf vollständig flachen 5×5 Vertex-Patches. Für die tieferen Baumwurzeln ist die untere Geländedifferenz zusätzlich begrenzt. Native Kontaktbeobachtung bleibt eigenständig.

Frei gehalten sind Arena samt voller Kronenhülle (Radius3100 plus Envelope), Arrival/Portal/Townlife (Radius2600 plus Envelope), Approach (360 Halbbreite plus niedrige Hülle und128), Nordrampe (350 plus Hülle und128), die aktuelle Bau-Fixture um (536100,-512000) (1000 plus Hülle) und der ganze neue Fußpfad. Der aktuelle Townlife-Scope hat Radius2200; seine Quellenmetadaten sind gebunden. Freie Bauflächen bedeuten die benannten reservierten Flächen; beliebige spätere dynamische Beete im Wald benötigen eine neue Platzierungs-/Navigationsprüfung. Die neue ESP verändert kein vorhandenes Beet.

20 Bäume ergeben rechnerisch 574,320 instanzierte Dreiecke; Steine10,080 und Gras6,720, insgesamt591,120 vor Culling/LOD/Engine-Verarbeitung. Dieser Umfang ist ein enger Kandidatenwert, keine gemessene Renderlast oder FPS-Zusage. Es gibt hier keine eigene LOD-/Windanimation. Eine spätere Verringerung des Refbudgets würde als neue Version erfolgen.

## Prüfscope und Native-Probe

Statisch geprüft: 16 gebundene Foundation-Contents ohne Kollision der beiden neuen IDs; unveränderte Quellen; TES3-HEDR/Masters und geschlossene STAT2/CELL1/FRMR68-Schemas; tatsächliche gespeicherte Float32-Transforms; 68 unabhängige VHGT-Anker; alle sechs freien Randtypen; Mindeststammabstand1024; Geometrie mit endlichen Werten, Normals/Indices/nondegenerierten Dreiecken, geschlossenem positivem Steinvolumen und expliziten Grasrückseiten; fünf gleiche Ausgaben beim deterministischen Neubau; gebundener ESMTool-Parser. Dieser Parser startet keine Engine.

Root-Probe: Referenzcounts und mindestens je drei repräsentative Baum-/Prop-Positionen, tatsächliche HeightMap-/World-Hits, Bodenauflage seitlich aus der Nähe, freie Pfadpunkte in beide Richtungen, echtes Gehen und Actor-onGround, Originalbereiche weiterhin frei, Kronen am nördlichen Wall und bei Pausen/Cellwechseln. Framezeitsamples erst nach Cell-/Meshladung, auf gleicher Position/Uhrzeit/Wetter/Resolution wie die Vergleichsprobe sammeln. Median/P95 und Stichprobenfenster binden; ein einzelnes FPS-Bild oder clean exit ersetzt diese Messung nicht.

## Eigene Quellen

Builder und Checker erhalten konkrete lokale Eingabepfade über Argumente; der eigene Frontier-Builder ist eine feste MIT-Quellenabhängigkeit mit SHA `300202c2d19493c715effe737fc6f08443512140993697706eab0747f9eef298`. `geometry-kernel.py` ist die exakt gebundene eigene MIT-Kopie mit SHA `19a1aae1b87e0555b747622dd11f3a7d6a13140623211e19b73bb964b5292c81`. Die Rebuild-Argumentliste darf private lokale Pfade enthalten und gehört ausschließlich in Work. Öffentliche Artefakte enthalten nur Rollen und Digests.

Eigene Geometrie/Texturabhängigkeiten: MIT. Crown-Borke bleibt die separat gebundene CC0-Abhängigkeit aus ihrem vorhandenen Modul. Keine NatureKit-/Bethesda-Geometrie oder große Paketabhängigkeit wurde übernommen. PLAN.md, Manifest, Preview und Prüfreceipts tragen die konkrete Candidate-Fassung. Neue Root-Nativebeobachtungen bleiben separate Receipts; die eingefrorenen Frontier-/Crown-/Plaza-Versionen bleiben erhalten.
