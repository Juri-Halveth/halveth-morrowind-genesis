# Worlds that remember · Elder Scrolls technology portfolio

**Juri / HALVETH · public technical overview · 4 November 2026**

This page collects the game and world technology that could be relevant to a conversation with Bethesda Game Studios. The centre is **Morrowind Genesis**, an existing OpenMW extension for *The Elder Scrolls III: Morrowind*. Three independent original-world prototypes show related ideas in other runtimes. They are separate products and cannot simply be dropped into a Bethesda engine.

**The proposed transaction is a one-time, as-is acquisition or negotiated licence of specifically identified original contributions.** It is not an offer to build or maintain a new game on commission. Scope, consideration, rights and delivery would need a written agreement. No Bethesda/ZeniMax relationship, approval, acceptance or future game integration is claimed.

> **Kurz auf Deutsch:** Genesis ergänzt ein lizenziertes Morrowind unter OpenMW um beobachtungsgebundene NPC-Chronik, einen eigenen Wanderer, lokale Dialoge, Figurensicht, Wissenswege und Lichtprofile. Realms, Portal Garden und ASHBOUND sind getrennte, eigenständige Prototypen für Weltzustand, Bücher, Entscheidungen, Bewegung und Darstellung. „Lebendige Figuren“ bedeutet hier implementierte Zustände, Verhalten und Kontinuität im Spiel – keine Behauptung von Bewusstsein.

## 1. The main playable integration: Morrowind Genesis

**Runtime:** OpenMW 0.51 on Windows, with a separately licensed Morrowind installation. [Source and setup](../../docs/SETUP.md) · [Public status](../../PUBLIC-STATUS.json) · [Native verification 1.0](../../docs/NATIVE-VERIFICATION-1.0.0.json).

| Player-facing capability | Where the implementation lives | Observed or tested boundary |
| --- | --- | --- |
| Native F6 character and world window: actual attributes, 27 skills, inventory, magic and nearby actors | [universe.lua](../../mod/scripts/halveth/universe.lua), [player.lua](../../mod/scripts/halveth/player.lua) | OpenMW integration checks and versioned native reports. No claim of every load order or screen size. |
| F7 knowledge, books, ingredient atlas and three exploration paths | [knowledge.lua](../../mod/scripts/halveth/knowledge.lua), [fieldcraft.lua](../../mod/scripts/halveth/fieldcraft.lua), [paths.lua](../../mod/scripts/halveth/paths.lua) | Game-state and save/reload checks; these are new bounded paths, not rewrites of original quests. |
| F8 local conversation with JARVIS or a selected actor, with player/actor/quest/book context | [player.lua](../../mod/scripts/halveth/player.lua), [server.py](../../server.py), [adapter contract](../../docs/OPENMW-ADAPTER.md) | One native framed chat roundtrip with an installed local model is documented. The free-text model is optional and separately installed. |
| Per-campaign, per-instance NPC memory and sourced speaking style | [server.py](../../server.py), [character_profile.py](../../character_profile.py) | Recorded local interaction and bounded game context; generated text can be wrong and does not become canonical lore. |
| NPC chronicle and regional faction pulse from loaded sightings and actual conversations | [worldlife.lua](../../mod/scripts/halveth/worldlife.lua), [world-life contract](../../docs/WORLDLIFE-0.8.md) | Save/reload with a real NPC in an isolated run. Unloaded regions do not advance as if observed. Original faction ranks are unchanged. |
| One owned wanderer with native AI wandering, pause, resume and exact-instance removal | [actor_life.lua](../../mod/scripts/halveth/actor_life.lua), [actor_life_global.lua](../../mod/scripts/halveth/actor_life_global.lua) | The 1.0 report records 82.6 game units of movement and an offscreen dismiss/revisit control. It is one actor, not a simulated population. |
| Three camera modes, bounded actor projection and a labelled viewpoint snapshot | [perspective.lua](../../mod/scripts/halveth/perspective.lua), [viewpoint contract](../../docs/PLAYER-PERSPECTIVE.md) | Native camera controls exercised. Projection inside a frame is not line of sight or an NPC's subjective experience. |
| Five atmosphere modes tied in part to game sun/storm state | [visuals.lua](../../mod/scripts/halveth/visuals.lua), [shader](../../mod/shaders/halveth_atmosphere.omwfx), [visual contract](../../docs/VISUAL-ATMOSPHERE.md) | Native checks cover selected interior/exterior states. This is a post-processing layer, not a new renderer or texture replacement. |

The game-to-companion bridge is deliberately narrow: framed UTF-8/JSON output in OpenMW logs, a local Python companion, and a session-bound JSON inbox. The four direct game actions are reviewed native operations. Model prose does not run arbitrary code. [Protocol and test boundaries](../../docs/OPENMW-ADAPTER.md).

### What “living” means here

The interesting engineering idea is a **continuity loop**, assembled from actual game observations:

`actor instance + campaign + place + game day + conversation → stored encounter → later context or bounded native action`

An actor's displayed history depends on observed loaded actors and saved events. The model may give a character a consistent voice, while the game retains authority over movement, inventory, quests and saves. This is useful as a design pattern for authored NPCs: distinguish **recorded encounter**, **derived simulation** and **generated speech**. It does not show open-ended cognition or autonomous simulation of the whole province.

### Measured baseline and open work

The public [1.0 native report](../../docs/NATIVE-VERIFICATION-1.0.0.json) records isolated OpenMW tests for exact NPC-context binding, selected-actor conversation, save/reload, owned-wanderer movement and removal, and a separate installed-0.9 regression. The [public status record](../../PUBLIC-STATUS.json) reports 71 local source/package tests at its recorded date. These are repository records, not a new full native run performed for this portfolio. A recipient should repeat them against the delivered revision and target hardware.

Open edges: broader personal-save and mod-load-order compatibility; physical input and resolution coverage; long-run frame rates; more than one original actor; richer non-scripted animation; authored quest alternatives; wider-world streaming; production voice and content review. [Current design transfer](../../docs/NEW-WORLD-DESIGN-TRANSFER.md) labels implemented items separately from ideas.

## 2. Related original-world work

| Project | Actual useful technology | Transfer route into an Elder Scrolls production | Evidence and licence boundary |
| --- | --- | --- | --- |
| [Genesis Zero](../../genesis-zero/README.md) | Self-contained WebGL2 ray-marched terrain, moving original creature, time/phase-controlled field projection and generated local ambience | Visual and interaction prototype; reimplement in target engine after evaluating performance and authorship | Browser graphics slice, not Morrowind/OpenMW and not a physics claim. |
| [Scarlet Garden / Realms](https://github.com/Juri-Halveth/halveth-realms/tree/22f3a706f88b0e186d9f6dc2807540e857ad2136) | Seeded terrain and places, individual interests/memories, 15-second world epochs while server runs, bounded shared local sessions, deterministic offline dialogue fallback | Reuse world-state schema or replay rules only after a versioned adapter and target-engine tests | Independent Electron/Three.js game; original code MIT, third-party notices remain. [README](https://github.com/Juri-Halveth/halveth-realms/blob/22f3a706f88b0e186d9f6dc2807540e857ad2136/README.md). |
| [Portal Garden](https://github.com/Juri-Halveth/halveth-unreal/tree/5dcd5ad655bcaa73e672618f0829100989484c65) | Native C++ seed world, portals, original reading/recipe/skill loop, enchantments, construction and local save state | Evaluate portable algorithms and content separately; Epic engine code/assets require their own terms and integration | Independent Unreal 5.8 prototype. Published 0.1 preview and separately recorded 0.2 native validation are different states. [README](https://github.com/Juri-Halveth/halveth-unreal/blob/5dcd5ad655bcaa73e672618f0829100989484c65/README.md). |
| [ASHBOUND](https://github.com/Juri-Halveth/halveth-scarlet/blob/c36150b55fe9ed4207f185d7092b3184c353df93/forschung/ashbound/README.md) | Six-place browser journey with persistent decisions and three outcomes; first-person spell/book prologue; separate native Unreal vertical slice | Story-state and spatial-spell design reference; a port needs a new implementation and rights review | Browser and native slices are distinct. The native slice has no NPC AI or full open world. [Native scope](https://github.com/Juri-Halveth/halveth-scarlet/blob/c36150b55fe9ed4207f185d7092b3184c353df93/native/ashbound-unreal/README.md). Scarlet has a file-specific licence history. |
| [SCARLET entity views](https://github.com/Juri-Halveth/halveth-scarlet/tree/c36150b55fe9ed4207f185d7092b3184c353df93/entities) | Editable spatial signatures, branches, checkpoints and a bounded event trail for 68 authored profiles | Character-design and continuity tool; review each profile's provenance and franchise references before a commercial transfer | A modelling interface, not 68 production NPCs or measured personalities. [Licence map](https://github.com/Juri-Halveth/halveth-scarlet/blob/c36150b55fe9ed4207f185d7092b3184c353df93/LICENSES.md). |

The common thread is **identity over time**: stable instance identity, observed encounters, authored memory, explicit transitions, reversible inspection and source-bound representations. The code is spread across different runtimes; this page does not pretend they already share one production engine or schema.

## 3. Local research lines awaiting a rights-cleared release

These candidates expand the technical inventory, but their bulk files, game-derived records, runtime profiles and generated assets are **not** part of this public repository or the proposed as-is source package yet.

| Local line | Concrete result | Current limit |
| --- | --- | --- |
| **Morrowind World Reforged 1.3.2** | A corrected LAND/VTEX map over the bound Morrowind, Tribunal and Bloodmoon master snapshots identifies 1,540 exterior grids and 123 nonzero texture paths. The candidate replaces 117 paths, preserves six ice or mixed ice/snow paths, and records exact path matches for all 123 in isolated OpenMW render routes. A fixed Azura's Coast sample includes camera motion and frame-time receipts. | `BECOMING`, not installed or visually accepted. One region route remains unresolved; missing images and broad performance remain open. The moving sample's p95 is above the 120-FPS frame budget, and unchanged runs varied materially. No new Elder Scrolls title is covered. |
| **The Meridian Wake / Veyrath design branch** | An original-world OpenMW target with a 72 × 54 planned cell map, generated terrain and Blender blockouts, nine candidate material maps, one static character blockout, story and faction records, and offline Hollow-field encounter prototypes. A separate larger fivefold planning grid and a small editable-voxel geology shadow explore world scale and excavation. | The latest Hollow v0.3 file was recorded as unlaunched and untested. The larger grid is a plan, the geology experiment is offline, and there is no native world, quest, NPC rig, navigation or playable total conversion. Veyrath is a naming/design branch, not a second shipped game. |
| **Morrowind Prestige 0.1** | An installed OpenMW 0.51 graphics profile with shader tuning, six generated architecture normal maps, UI scaling and a launcher-path repair. Its local receipt records an engine run with a fresh test character in Seyda Neen and Balmora at 1600 × 900. | No accepted native before/after visual comparison or measured performance gain. Private graphics-pack licences remain separate. |
| **Entity Life 0.1** | A local TES3 record/placed-instance catalogue distinguishes stable logical IDs, source addresses, templates and changing visual states; a separate Bash demonstration journals chosen presentation/story rules. | The catalogue is made from bound licensed local game records and is not uploaded here. Dynamic in-game actors and branching quests need native adapters. The hash chain alone does not authenticate origin or demonstrate consciousness. |
| **Human-body research model** | A local anatomical/growth model records source-bound dimensions, shape and sampled ground-contact constraints; its earlier report records nine model checks. | No walking rig, native clothing/animation link, visible game acceptance or biological realism claim. It is a design and geometry candidate. |
| **Morrowind First world-reception rules** | A local policy prototype models opt-in reception, an isolated guest arena, text/mail, gift depot and one-time delivery; its report records eleven rule checks. | No real visitor identity verification, network listener, guest spawn, item delivery or multiplayer runtime is implemented. |

The terrain line's strongest reusable contribution is its **source-to-render audit method**: bind a master-file snapshot, resolve LAND/VTEX semantics, sample the actual engine path, and keep camera, timing and visual acceptance as separate results. The Meridian Wake line contributes **world-planning and stateful quest design**; it still needs one native, playable region before a production claim. The other local lines add source/instance identity, a tested visual profile, a body-design target and scoped cross-world rules. These lines are disclosed here as research summaries only. Their private source and assets require a separate provenance and rights review before transfer.

## 4. A practical evaluation path

1. **Open the native Morrowind slice.** Use the documented source setup with owned game files; inspect one actor in F6, speak via F8, revisit via Weltleben, save/reload, then inspect the same actor's history. Compare the recorded actor instance, not only the base NPC name.
2. **Check the independent controls.** Run the public source tests and repeat the native smoke sequence on a disposable save. Record OpenMW version, mod order, game data entitlement, model availability, action IDs, timestamps and any errors.
3. **Choose a target-engine experiment.** Port a single *abstract* capability—such as encounter history or quest-state-safe dialogue context—into a separate owned prototype. Specify the target interface, data schema, latency, replay rule and authorial review. Do not assume OpenMW Lua, Electron JavaScript or Unreal 5.8 assets are plug-compatible with Creation Engine.
4. **Review rights by file and revision.** Identify original code, original art, pre-existing open licences, engine dependencies, third-party content and private player data before considering any transfer.

The official [OpenMW Lua documentation](https://openmw.readthedocs.io/en/stable/reference/lua-scripting/overview.html) defines the script scopes and save/load mechanism relevant to step 1. It says nothing about Bethesda's internal technology or acceptance of this proposal.

## 5. Delivery and rights boundary

**Potential as-is delivery, if agreed:** a fixed source revision, a file/rights manifest, reproducible build and test instructions, versioned native receipts, and the specified original assets that pass provenance review. Acceptance criteria would be written for that fixed handoff. Continued development, support, custom integration and new content are separate matters and are not included by default.

**Not represented as transferable by this page:** Bethesda game data, Morrowind dialogue/books/quests, user saves, extracted lore, OpenMW binaries, model weights, Epic/Unreal engine assets, downloaded third-party packs, private conversations, credentials or uncertain-origin character material. Generated artwork must be checked against its recorded provenance and applicable terms before any asset-level grant.

The Morrowind Genesis repository is MIT-licensed for its own code and documentation, and it has separate CC0-labelled art with stated limits; see [LICENSE](../../LICENSE), [asset notice](../../ASSET-LICENSE.md) and [third-party notices](../../THIRD-PARTY-NOTICES.md). Realms and Portal Garden publish their own MIT code; Scarlet has a different, revision-sensitive licence map. Existing public grants do not disappear because a later buyer receives a licence. Under German law, the author's copyright itself is normally not transferable, while defined exploitation rights can be granted; the exact sale structure would require agreement. [German Copyright Act §§ 29, 31](https://www.gesetze-im-internet.de/urhg/BJNR012730965.html).

ZeniMax's [Terms of Service §§ 2 and 16](https://bethesda.net/data/tos/en.html) reserve commercial use of game-derived content without express written permission and say it does not accept unsolicited creative material; § 16 also describes non-confidential treatment and rights consequences for material nonetheless sent. Accordingly, this public portfolio is a **self-published overview**, not a claim that ZeniMax received or accepted an acquisition offer. A direct handoff should start with an agreed submission route, written permission where needed, and terms before any non-public source or creative packet is sent.

## 6. Source binding

The frozen repository heads used to build this overview are in [SOURCE-SNAPSHOT.json](SOURCE-SNAPSHOT.json). The inventory gives each project its own runtime and claim ceiling, and separately lists the local candidates described above. It is a finite review of identified game-related sources, not a statement that every past local experiment or every file on the machine was audited. Private saves and bulk local graphics assets are outside this public packet.

**Contact for a negotiated one-time source/rights discussion:** use the GitHub repository's public issue or profile contact route to request a suitable channel. Do not put private source, personal data or proposed price in a public issue.
