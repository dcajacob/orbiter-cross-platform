# Current Windows paused world replacement

Fresh Debug and Release application/SDK/client builds at `bdfd067f` pass the
unchanged paused Atlantis resupply scene for twenty normally closed worlds in
each automatic/SSE2 profile. The four actual simulator processes complete
80 worlds, 76 real launchpad restarts, 4,800 successful presents and 80 clean
graphics-context deletions. All 14,400 per-frame vessel rows are finite at time
zero, with the complete original three-vessel roster, reciprocal ISS docking
and both Leonardo attachment links intact. Every process exits normally.
Both builds also pass all 28 unit tests.

The earlier `f3e86add` campaign passed twenty Debug/automatic worlds, then crashed
opening Map MFD in Debug/SSE2 world seventeen after sixteen normal cleanups.
Map's static saved owner/body pointers survived world deletion. Reusing the
vessel address could therefore restore a retired body pointer. The repair
invalidates world-owned pointers in the nine built-in MFD caches at the existing
GlobalExit boundary, after MFD destruction and before world reset. Same-world
restoration, scalar preferences, instance layout and the public SDK are
unchanged. The actual Map methods and cleanup methods also pass the focused
[controlled regression](../../Tests/Production/MfdWorldCache/README.md).

The independent Linux audit re-reads all 1,089 raw files, actual simulator
PID/exit/timeout receipts, the new guest-agent/normal-user/private-desktop chain,
ordered starts/normal cleanups/launchpad selections, every vessel row, original
input hashes and every per-world renderer/context record. Loaded application
and driver hashes bind to the independently preserved 9,486-member build closure
and immutable source. It independently verifies all 69 pinned Mesa DLL/license
files and the exact source-built zlib export/import binding. The one established
Dragonfly mesh-delivery alias is checked against its original source bytes;
Windows module path spelling is compared with Windows case semantics.

The [verification record](WindowsAttachmentLifetimeVerification.json) pins the
completed independent audit and raw archive. Earlier failed captures and audit
attempts remain retained locally. The new capture uses normal `--scenario`
cleanup with `ShutdownMode = 0`; fast `--scenariox` shutdown cannot satisfy it.
Process-heap and Debug CRT checks supplement this regression. It is not Windows
ASan or leak qualification, numerical/image flight parity, class admission or
Phase 6 completion. Raw evidence remains local.
