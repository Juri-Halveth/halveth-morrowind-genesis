# Finite validation scope

This source package contains three distinct checks:

1. Eleven Python rule tests bind the declared local reception/depot/courier
   model. Caller strings are declared roles; no network endpoint is present.
2. Thirteen controller/download tests run with fake engine and fake HTTP
   executables. They check spaces in paths, original configuration restoration
   after successful and failed starts, restoration after a failed configuration
   copy, known probe exclusion, explicit saves, retained stale locks, pinned
   download bytes, and failure cleanup. They passed in Linux Bash and native
   Windows Git Bash. They do not measure game frame rates or render a scene.
3. Twelve Lua 5.1 HUD tests use declared engine packages. Native HUD rendering and
   API integration are a separate observation, recorded when a real engine run
   with the exact source digest is available.

The Bash essence harness checks file snapshots/verification, a rejected nested
manifest, temporary cleanup after successful and failed commands, retained
before/after differences, and exact tool-version first-line binding.

The source packaging tool checks an explicit own-source allowlist and bounded
text patterns. ZIP construction checks exact source-byte roundtrips and CRCs.
Four synthetic publication-boundary tests check omitted game/private files,
rejected machine paths, rejected key/token strings, and rejected binary bytes.
Those checks bind file content and declared contracts. They do not constitute
a complete system audit, authentication proof or production equivalence.

The [courier receipt](COURIER_NATIVE.json) records fourteen native checks in
OpenMW 0.51.0: a disabled depot, delayed dispatch, real NPC creation/approach,
the actual inventory transfer of both items, and an ignored duplicate claim.
The fixture uses accelerated game time and a single synthetic parcel. Its five
production module files are bound by exact source digests. Save/reload evidence
is recorded separately from this first source freeze.

Existing inventory-stack merges, all navigation
meshes/interiors, long-run frame pacing, complete campaigns, visitor networking
and cross-server authentication require their own checks.
