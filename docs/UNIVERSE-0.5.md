# Native Morrowind expansion, version 0.5

The playable target is the existing TES III world in OpenMW 0.51. One visible game entry starts that world and its optional local dialogue service. All player-facing additions in this milestone are Lua UI or native records inside Morrowind.

## What changed

- Character view: actual attributes, dynamic values and all 27 skills.
- Inventory: complete current inventory, twelve item categories, name/category search, equipped markers and value/weight sorting. Details explain damage, condition, effects and known ingredient properties.
- Magic: actual learned spells with their native parameters; selecting a spell uses the engine's normal spell selection.
- Encounters: loaded actors within 3,000 game units, actual class/race/services/disposition and conversation targeting of the selected instance.
- NPC direction: stable authored speech styles plus current runtime facts and recorded conversations. Creature responses describe behavior instead of inventing a human biography.
- Native mouse entry: buttons in the normal inventory and dialogue lead to F6, F7 and F8 views.
- Typography: an antialiased configuration for OpenMW's existing MysticCards font. No font binary is distributed.

These changes supplement existing books, learning, LOVE/SPARK/AEGIS and graphics packages. They do not replace the game's authored quest engine with generated prose.

## Bound local inventory of the universe

The new `scripts/survey_universe.py` walks every record and subrecord boundary in the active TES3 plugin files. It records byte positions, hashes, identities, source order, overrides and deletion markers in a local SQLite register. Three tests cover byte coverage/override resolution, malformed boundaries, and distinct exterior cell identities.

The checked installation contained **95,200,284 plugin bytes, 70,263 records and 43 record types**. Its effective records include:

| Type | Count |
|---|---:|
| NPC definitions | 3,049 |
| Creature definitions | 399 |
| Books and scrolls | 638 |
| Spells | 1,068 |
| Enchantments | 808 |
| Weapons | 652 |
| Armor | 422 |
| Cells | 2,893 |
| Dialogue INFO records | 32,148 |
| Scripts | 1,215 |

These counts describe one load order, not every Morrowind installation. The full register contains game-derived content and stays local. BSA textures, mesh geometry, audio decoding and every possible script branch are outside this structural pass.

The existing installed appearance adapter supplies head model mappings used by **3,045 of the 3,049 NPC definitions** and hair mappings used by 2,831. The four remaining head references include Argonian vampire heads and a dialogue placeholder. They were retained instead of assigning an unrelated face. Model mapping coverage is not a visual or animation check of every character, and these head models predate version 0.5.

## Development branches retained

| Branch | Current implementation | Next concrete native step |
|---|---|---|
| HALVETH: understandable abilities | Skill, item and spell explanations | Add contextual craft lessons tied to observed practice |
| LUCINET: connected knowledge | Local lore, book journal, source-bound NPC context | Relate selected quest facts to cited local records |
| LOKI: alternatives | Conversation alternatives and existing reviewed actions | Implement one authored peaceful quest branch with prerequisites and a save/reload test |
| RACHEL: continuity | Separate instance/world memory; bounded state observations | Add an in-game intention/task journal with explicit completion events |
| LOVE: care and beauty | Native healing spell, owned artwork, existing beauty profile, improved typography | Add a native visual effect with a measured gameplay check |
| Graphics and characters | Existing third-party heads/hair/textures/shaders | Compare representative races, lighting and animations before another asset package |
| Movement and combat | Existing engine controls | Prototype one bounded movement mechanic without replacing normal control ownership |
| Voices and sound | Existing game audio; text model replies | Add optional local speech only after an actual latency/resource test |
| Construction and new regions | Requested future branch | Define one native building placement rule or authored cell transition |

These are implementation meanings chosen for this project, not claims that a name or symbolic principle supplies an engine capability. Future content remains native to Morrowind. No external game launcher is created by this roadmap.

## Evidence and limits

The real-engine test covers 27 skills, twelve inventory families, twenty fixture inventory entries, seven nearby actors, searching, selecting LOVE, opening the normal book reader and retaining a borrowed inventory mode. Operator mouse review covered the new normal-menu bar and tabs at 1280×720.

A separate actual Arrille round trip passed through the native dialogue, companion, local `hermes3:8b` model and matching in-game reply. His Trader class, Barter/Spells services and disposition came from the running game. That one response was grammatically imperfect and longer than requested. It proves a working route, not fully polished personalities for all NPCs.

See [the source-bound native summary](NATIVE-VERIFICATION-0.5.0.json). Hotkeys are wired, but physical F6/F7/F8 injection was not verified. The clickable route was observed. There is no claimed whole-world semantic rewrite, new renderer, universal mod compatibility or guaranteed frame rate.

## Sources used

- [Gamefinity: Spieleentwickler erklärt](https://gamefinity.net/spieleentwickler-erklaert/) informed the separation of design, programming, narrative, art, audio, QA and delivery work. It is not technical engine documentation.
- [OpenMW 0.51 Lua API](https://openmw.readthedocs.io/en/openmw-0.51.0/reference/lua-scripting/api.html) and the matching installed API supplied the native actor, inventory, spell and UI interfaces.
- [OpenMW font configuration](https://openmw.readthedocs.io/en/latest/reference/modding/font.html) supplied the `.omwfont` configuration route.
- [OpenMW 0.51 alchemy source](https://github.com/OpenMW/openmw/blob/openmw-0.51.0/apps/openmw/mwmechanics/alchemy.cpp) informed ingredient-effect visibility thresholds. The extension respects `fWortChanceValue` instead of revealing every ingredient effect immediately.

Own implementation and documentation are MIT. Original game content, installed graphics packs and OpenMW retain their own licenses. The public package contains the extension source and previously approved original artwork, not the extracted game register.
