# Generation-Atelier für HALVETH · Morrowind Genesis

Quellenstand: **2026-09-23T00:29:19.162Z**. Die fünf Werkzeugwege und drei kopierbaren Produktionsbriefs sind in `data/generation-providers.json` hinterlegt. Die Briefs sind Arbeitsaufträge; es wurde dadurch kein Anbieter aktiviert und noch kein Asset erzeugt.

## Status lesen

- `READY_LOCAL_BRIEF`: Der Arbeitsbrief lässt sich lokal verwenden. Dieser Status bestätigt keine installierte App, keinen Exporter und keinen fertigen Import.
- `REQUIRES_PROVIDER_ACCESS`: Der Brief ist vorbereitet; Konto, Produktzugang, Credits oder Lizenz müssen für die tatsächliche Ausführung vorhanden sein. Keine Anmeldung, Bestellung oder bezahlte API-Ausführung ist Bestandteil dieser Dateien.

Blender führt den ersten Status. Adobe Firefly, After Effects, Meshy und Dreamina/Seedance führen den zweiten. Bei After Effects betrifft dies insbesondere die lokale App-Lizenz; es ist keine Behauptung, dass jeder Render cloudbasiert wäre.

## Spielassets und Filmzweig

**Scarlet Love Banner** beschreibt im Produktionsbrief einen flachen 1024 × 2048-Pixel-Texturmaster; die mitgelieferte Imagegen-Fassung hat tatsächlich 887 × 1774 Pixel. Der Zielentwurf trägt ein eigenes Herz-/Mottenornament. Er wird über die UVs eines Bannerobjekts zur Spieltextur. Adobe dokumentiert Bildgenerierung und PNG/JPG/GIF-Export; Sampler kann Materialkanäle separat ausgeben. [Photoshop-Bilder](https://www.adobe.com/products/photoshop/generate-image.html), [Photoshop-Export](https://helpx.adobe.com/photoshop/using/export-artboards-layers.html), [Sampler-Export](https://helpx.adobe.com/substance-3d-sampler/using/export.html).

**Astral Moth Shrine** ist eine statische Requisite. GLB ist der Austauschmaster. Blender importiert glTF-Meshes, Materialien, Texturen und weitere Daten. Seine glTF-Normalmaps verwenden +Y; die OpenMW-Dokumentation nennt DX-Normalmaps. Die Ableitung muss deshalb bewusst konvertiert und sichtbar geprüft werden. GLB oder FBX einfach in NIF umzubenennen erzeugt kein kompatibles Modell. [Blender-glTF](https://docs.blender.org/manual/en/latest/addons/import_export/scene_gltf2.html), [OpenMW-Texturen](https://openmw.readthedocs.io/en/stable/reference/modding/texture-modding/texture-basics.html).

Der OpenMW-NIF-Pfad benötigt einen kompatiblen Blender-Exporter. Die OSG-Pipeline eignet sich für statische Modelle. Zielpfade des Briefs sind `Meshes/halveth/astral_moth_shrine.nif` und externe Texturen unter `Textures/halveth/`; die eigentliche Verpackung folgt dem getesteten Exportweg. Vor Spielintegration: Vorschau in OpenMW-CS, separates Test-Addon, Maßstab/Kollision/Licht prüfen. [NIF-Pipeline](https://openmw.readthedocs.io/en/stable/reference/modding/custom-models/pipeline-blender-nif.html), [OSG-Pipeline](https://openmw.readthedocs.io/en/stable/reference/modding/custom-models/pipeline-blender-osgnative.html).

**Scarlet Settlement** ist ausdrücklich ein achtsekündiger Film. Seedance liefert MP4; After Effects rendert Filme oder Einzelbildsequenzen. Beides eignet sich für Intro, Trailer und Lore-Szenen. Der Film belegt keine Echtzeitgrafik, NPC-Simulation oder begehbare Welt. [BytePlus-LAS](https://docs.byteplus.com/en/docs/Byteplus_LAS/video_gen_enhanced), [After-Effects-Export](https://helpx.adobe.com/after-effects/using/basics-rendering-exporting.html).

## Quellengebundene Zugangsgrenzen

| Werkzeug | Belegter Stand | Noch zu prüfen |
|---|---|---|
| Adobe Firefly / Photoshop | Generative Credits und Premium-Funktionen sind planabhängig. | Nutzerplan, Guthaben, gewähltes Modell und konkrete Ausgaberechte. [Credits](https://helpx.adobe.com/firefly/web/get-started/learn-the-basics/generative-credits-overview.html). |
| After Effects | Render Queue und Media Encoder liefern Filme bzw. Bildfolgen. | Lokale Installation, Lizenz, Codec und Export. |
| Meshy | GLB/FBX/OBJ und weitere Austauschformate. Die aktuelle Free-Hilfe nennt 100 monatliche Web-Credits, aber keine regulären Downloads und keinen API-Zugang. | Vorhandener Paid-Zugang, API-Credits, tatsächliche Qualität und Lizenz bei Erzeugung. [Formate](https://docs.meshy.ai/en/api/text-to-3d), [Free-Plan](https://help.meshy.ai/en/articles/15696428-what-is-included-on-the-free-plan), [Rechte](https://help.meshy.ai/en/articles/16102098-can-i-use-meshy-assets-commercially). |
| Dreamina / Seedance | Der geprüfte BytePlus-LAS-Vertrag nennt 2.0 mit 4–15 s/24 fps/bis 4K und Modusgrenzen; 2.5 mit 4–30 s/24 fps/480–720p. | Diese Werte gelten für den dokumentierten LAS-Weg und sind keine Zusage zum Dreamina-Nutzerplan. Konto, Preis, Export und Nutzungsbedingungen offen. [LAS-Vertrag](https://docs.byteplus.com/en/docs/Byteplus_LAS/video_gen_enhanced), [Dreamina](https://dreamina.capcut.com/tools/seedance-2-0). |
| Blender lokal | Offizielle glTF-Import-/Exportdokumentation sowie OpenMW-Konvertierungspfade vorhanden. | Installierte Version und passender NIF-/OSG-Exporter; `latest`-Dokumentation ist kein Test des lokalen Systems. |

Meshy-Auto-Rigging ist auf geeignete texturierte humanoide Zweibeiner beschränkt. Der Schreinbrief braucht bewusst kein Rig. Spätere NPCs erfordern zusätzlich passende Morrowind-Skelette, Körperteile, Animationsgruppen und Ausrüstungstests. [Rigging-Vertrag](https://docs.meshy.ai/en/api/rigging).

## Annahme eines erzeugten Assets

Ein Asset wird erst nach den Akzeptanzpunkten des jeweiligen Briefs übernommen. Generatorwünsche wie Dreieckszahl, Auflösung und Dauer sind bis zur Dateiprüfung Zielwerte. Die Ausgabe erhält eine Herkunftsnotiz mit Prompt, Anbieterprodukt/Modell, Erzeugungszeit, zulässigen Referenzen, Lizenz/Attribution, Quellmaster und Prüfsumme. Engine-Ableitungen bleiben getrennt vom unveränderten Master. Gameplay- und Questdaten werden nicht zur bloßen Grafikinstallation umgeschrieben.

Die Recherche ist ein endlicher offizieller Quellenstand. Es wurden weder Providerkonten noch tatsächlich generierte Dateien geprüft; eine Anbieterbeschreibung garantiert keine Bildqualität oder lokale Importfähigkeit.
