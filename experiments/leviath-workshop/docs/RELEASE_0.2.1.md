# Workshop 0.2.1: CI preparation and path assertions

This patch preserves the frozen 0.2.0 game modules, installer, controller,
assets and native receipts. It changes two test oracles, the CI preparation
order, package version metadata and this release documentation.

The two Windows assertions now compare resolved paths on both sides. The
hosted runner supplied a temporary directory through its `RUNNER~1` spelling,
while the installer recorded the same directory through its resolved spelling.
A separate regression plans through a real `..` alias, then changes a bound
existing source and verifies that application still rejects it before creating
the new profile. Referenced game content remains outside the copied payload.

The CI now runs the frozen HUD 0.1.4 PNG generator before its checker. The
generator prepares a build receipt required by that checker. Generated PNG
bytes must still match the existing source and native asset binding; the
collector retains that exact check.

The original 0.2.0 head had two successful base-repository Source checks and
two failed workshop runs. Its Windows jobs reached 55 tests with two path
assertion failures; its Ubuntu jobs passed 55 tests and then reached the
missing HUD build receipt. Those failed runs and the 0.2.0 archive remain
historical observations. A local hotfix check and a fresh hosted result are
separate states. Hosted CI checks source, models and package boundaries; it
does not replay the local native game tests.

Local Windows Git Bash validation passed 56 Python regressions, 11 delivery
rules, the Bash essence checks, 36 Lua syntax checks and the unchanged declared
Townlife/HUD models (22 and 20 checks). A fresh disposable CI copy ran both
PNG build/check pairs and then the accepted collector: all 215 collected
files remained byte-identical, including the 98-byte HUD PNG. No engine
execution was needed for this test/workflow patch. Hosted CI for a published
hotfix remains a separate fresh result.
