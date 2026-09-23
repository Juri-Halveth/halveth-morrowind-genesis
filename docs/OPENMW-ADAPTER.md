# OpenMW adapter — Genesis 0.1

This is an additive OpenMW 0.51 Lua mod (API revision 129). Its F8 window provides free text, replies and four bounded native world tools. Original dialogue remains available. The mod does not patch quests, dialogue records, economics, the vanilla executable or existing save files. The +250 button creates 250 gold directly; it neither implements nor disables an existing 250-gold dialogue loop.

## Real transport

OpenMW Lua is sandboxed: there is no LuaSocket, HTTP client, general `io`, DLL loading or operating-system command execution. This adapter uses available documented mechanisms:

1. Lua serializes each context, chat or result record to UTF-8 JSON, divides it into chunks of at most 384 bytes and prints short ASCII hex frames to the OpenMW log.
2. The external local companion validates and reassembles those frames, decodes the complete JSON event and creates plain JSON responses.
3. The companion replaces the existing loose file `mod/bridge/inbox.json` atomically. The file must exist before OpenMW starts so its name enters the VFS index.
4. The player script reopens `bridge/inbox.json` using `openmw.vfs` every 250 ms, checks a 64 KiB limit and decodes it through `openmw.markup.decodeYaml`, which accepts JSON. It does not load responses as Lua source.

This reopening design is supported by the OpenMW 0.51 source: `Manager::findNormalized` calls `File::open` on each lookup; `FileSystemArchiveFile::open` reopens its filesystem path. It must be a loose file, not an archive member. Response delivery works while the world is paused because interval measurement uses `core.getRealTime()` inside `onFrame`.

The short frames are necessary in the tested Windows engine: a long single log line was observed with an OpenMW timestamp inserted inside the original chat text. JSON remained parseable, so checking only that a reply arrived missed the changed wording. The framed rerun compared the complete Unicode request and independently submitted native source context before claiming success.

## Installation contract

The isolated profile helper should append the absolute `mod` data directory and `content=halveth.omwscripts`. A running game must be restarted after first installation. No MWSE or engine modification is required. Keep generated `.local` state and extracted game data out of published source.

Press **F8**, choose **JARVIS** or **NPC**, click the input area, type and press Enter or click **Senden**. JARVIS is the default. NPC mode binds the context's actual selected actor; a label distinguishes dialogue target, crosshair actor and nearest actor. Direct buttons work without the AI companion: heal, +250 gold, travel to this session's starting position, and return to the previous travel point. Free conversation requires the companion process. The original menus remain usable.

## Protocol version 1

Each current transport line uses `HALVETH_FRAME:<messageId>:<part>:<count>:<hex>`. Parts are numbered from 1; each holds at most 384 source bytes. OpenMW adds its own timestamp/script prefix before the marker. The reader rejects malformed/conflicting frames, limits an assembled event to 64 KiB and expires incomplete assemblies after 15 seconds. Only the complete UTF-8 JSON is decoded. Legacy `HALVETH_EVENT:<JSON>` input remains readable by the companion; the mod sends framed data.

Logical reconstructed event:

```json
{"type":"chat","sessionId":"omw-...","requestId":"chat-...","entityMode":"jarvis","text":"Hallo!","context":{}}
```

`context` events contain `sessionId` and `context`. The context object has:

- `player`: game object `id`, base `recordId`, name, race/class, cell, x/y/z position, gold and `{current,max}` values for health, magicka and fatigue.
- `npc`: current dialogue target, a crosshair actor, or nearest actor. `selectionMethod` specifies which. It may also be a creature; this does not claim a speaking personality exists in the original game.
- `nearby`: up to 12 actors sorted by distance, with instance IDs distinct from base record IDs.
- `quests`: up to 100 quest IDs/stages. This is a bounded context window, not complete lore extraction.
- `book`: most recently opened book, limited to 14,000 bytes with an explicit `truncated` flag. Raw local game text stays local.
- `anchors`: currently the single `session_start` point, captured from the engine when the player session registers.
- `engine.apiRevision` and `gameTime`.
- `worldId`: persisted through the mod's save/load record. It stays distinct from the new connection `sessionId` on every load. NPC memory keys combine world ID and instance ID so two generic actors sharing a base record remain separate. Loading an old save with no Genesis record creates a new world ID; save once with the mod enabled to preserve that campaign identity.

Inbound mailbox:

```json
{
  "sequence": 1,
  "sessionId": "the-current-session-id-from-context",
  "reply": "Ich bin bereit.",
  "requestId": "chat-request-id-if-replying-to-an-in-game-message",
  "speaker": "JARVIS",
  "action": {
    "id": "action-unique-001",
    "kind": "give_gold",
    "params": {"amount": 250}
  }
}
```

`reply` and `action` are optional. Sequence is a monotonically increasing integer within the current session, at most 2,147,483,647 because of the native YAML decoder's integer range. Do not use epoch milliseconds as an integer sequence. Preserve the counter across companion restarts while the same game session remains open. A new game, save load or script reload creates a new session ID. Old-session mailbox content cannot execute in that new session. A companion must serialize mailbox writes and await the action result before replacing an unacknowledged action with another one. Replies should carry the originating `requestId`; unrelated or late replies are discarded by the in-game UI. Native chat accepts one pending message at a time, up to 4000 Unicode characters.

The fixed action vocabulary is:

| Kind | Parameters | Native implementation |
| --- | --- | --- |
| `heal_player` | `{}` | Player-local dynamic health, magicka and fatigue current values set to their current maximums |
| `give_gold` | `{"amount":250}` | Global `world.createObject('gold_001', amount):moveInto(types.Actor.inventory(player))`; integer range 1–1,000,000 |
| `teleport_anchor` | `{"anchor":"session_start"}` | Global `player:teleport` to the engine-captured starting point, preserving a return point |
| `return_anchor` | `{}` | Return to the previous captured travel point |

Actions carry distinct IDs. The player and global scripts reserve IDs before applying effects. Duplicate IDs do not reapply an action. The global handler waits five frames, reads the engine state, then returns:

```json
{"type":"result","sessionId":"omw-...","actionId":"action-unique-001","kind":"give_gold","success":true,"message":"250 Gold erschaffen.","before":{"gold":0},"after":{"gold":250}}
```

Receipts include health/magicka/fatigue, cell and position. A positive result requires the expected postcondition in the sampled state. This is not a full save rollback system. Return-point travel is reversible movement; created gold and healing are ordinary changes in the active game.

## Native test and extension points

The player interface is `require('openmw.interfaces').HALVETH` with `open()`, `getSessionId()` and `requestAction(kind, params, optionalId)`. In OpenMW's `luap` console it is available as `I.HALVETH`.

The isolated smoke helper sends the bounded local event `HALVETH_TestRequest` with `{kind='give_gold', params={amount=250}, id='smoke-gold-once'}`. `HALVETH_TestOpen` builds the same F8 window. Neither interprets code or expands the action vocabulary. Smoke scenarios must use a disposable character and separate save/log directories.

The optional `tests/integration_chat.py` uses `HALVETH_TestChat` to enter text through the same native window/submit function. `HALVETH_ChatSubmitted` carries a local source snapshot to the test observer. After a matching reply has been appended to the transcript, the mod emits `reply_received` and sends `HALVETH_ReplyReceived` locally. These receipts distinguish a generated model answer from one actually consumed by the native dialog.

Official API supports further local lore extraction through `types.Book.records`, `types.NPC.records`, `core.dialogue.topic.records` and `core.dialogue.journal.records`. Dialogue conditions must remain associated with each record: a line existing in the database does not mean the current NPC would say it at the current quest stage. Generated personality/memory is an authored layer, separate from the source-game record.

## Verification

- All three scripts compile with the installed OpenMW Lua 5.1 library.
- A real isolated OpenMW run loaded the mod, emitted player/nearby context and applied +250 gold: native inventory before 0, after 250, process exit 0, no Lua errors in that run.
- An extended native run kept gold at 250 after replaying the same action ID, restored damaged health from 1 to 35/35, and constructed/opened/closed the in-game window without Lua errors. Visual layout inspection is separate from this API check.
- A final framed native chat run used the installed `hermes3:8b` model in `MODEL_LIVE` mode. Exact original Unicode input and full source context matched; the native dialog consumed exactly the model's reply with the matching session/request ID, speaker JARVIS and its window open. Model response time in that run was 1.217 seconds; no world action was offered or executed. The process exited with code 0 and no Lua errors. This is one measured run, not a latency guarantee or visual screenshot check.
- Broader UI, mailbox, action and model checks are recorded in the project verification output as they run. This document does not claim a full NPC replacement, engine-wide AI autonomy, voice control, new terrain, downloaded texture pack or arbitrary quest repair.

## Version-bound primary references

- [OpenMW 0.51 language sandbox](https://openmw.readthedocs.io/en/openmw-0.51.0/reference/lua-scripting/overview.html)
- [VFS API](https://openmw.readthedocs.io/en/openmw-0.51.0/reference/lua-scripting/openmw_vfs.html)
- [Markup JSON/YAML decoding](https://openmw.readthedocs.io/en/openmw-0.51.0/reference/lua-scripting/openmw_markup.html)
- [Player/global engine handlers](https://openmw.readthedocs.io/en/openmw-0.51.0/reference/lua-scripting/engine_handlers.html)
- [UI layouts](https://openmw.readthedocs.io/en/openmw-0.51.0/reference/lua-scripting/user_interface.html)
- [Core objects, teleport, dialogue and clocks](https://openmw.readthedocs.io/en/openmw-0.51.0/reference/lua-scripting/openmw_core.html)
- [Actor/NPC/book/player APIs](https://openmw.readthedocs.io/en/openmw-0.51.0/reference/lua-scripting/openmw_types.html)
- [Object creation](https://openmw.readthedocs.io/en/openmw-0.51.0/reference/lua-scripting/openmw_world.html)
- [0.51 VFS filesystem reopening implementation](https://github.com/OpenMW/openmw/blob/openmw-0.51.0/components/vfs/filesystemarchive.cpp)
- [0.51 VFS manager implementation](https://github.com/OpenMW/openmw/blob/openmw-0.51.0/components/vfs/manager.cpp)
- [0.51 Lua print-to-log implementation](https://github.com/OpenMW/openmw/blob/openmw-0.51.0/components/lua/luastate.cpp)
