# Hosted Windows path oracle repair in source 0.1.2

At source head `4c23a85bbf4c7bfc368470400ee741a81c4ceb74`, the Ubuntu
workshop job passed. Two Windows jobs failed the same single test assertion:

- [Windows workflow run 37091113665](https://github.com/Juri-Halveth/halveth-morrowind-genesis/actions/runs/37091113665/job/111111473247)
- [Windows workflow run 37091111356](https://github.com/Juri-Halveth/halveth-morrowind-genesis/actions/runs/37091111356/job/111111466682)

Both logs show `test_provision.py:74` raising `ValueError: substring not
found`; the other 27 tests passed. That assertion searched the rendered
configuration for the fixture's raw path spelling. The provisioner binds and
renders resolved paths. The logs did not record both path strings, so the exact
runner alias is not independently observed.

The old assertion was reproduced against real disposable Windows files by
passing an existing directory followed by `..`. It names the same directory
but has a different raw spelling. Provisioning retained the original bytes
and rendered the correct canonical data reference; the old substring lookup
still failed at the same line.

The repaired test resolves its five expected path references and adds a real
noncanonical-input regression. It still checks complete base data order,
content/fallback interleaving, distinct own copies, private write destinations,
and preserved original/hardlink bytes. The configuration contains no `/../`
components. This changes the test oracle; production installer, launcher,
Lua modules and workflow action pins retain their 0.1.1 bytes.

The local suite now has 29 tests: 14 controller/download, nine provisioner
fixtures and six publication-boundary tests. Hosted CI acceptance belongs to
the new source head after transfer; local checks do not relabel the old failures.
