# Original legacy station observations

**Version 1 limitation:** subsequent native testing exposed that the rescue
fixture used `Behavior.scn` and did not stage its named flight recordings.
The original application silently fell back from requested playback. The three
non-playback cases retain their audited observations; the rescue case is
unqualified for the intended complete stock playback. All version 1 bytes remain
pinned and preserved. Full reference replay/comparison is blocked until corrected,
versioned observations include the original entry point and every recording.

The version 2 producer uses `cases-v2.json`, retains each original relative
scenario filename, and pins all 22 files in `Flights/Smack! Rescue`. Both
observers record the actual public SDK `Playback()` flag for every vessel at
ticks 0 through 60. All seven rescue vessels must remain in playback; the other
three cases must remain outside playback. Five damaged-copy controls reject a
missing position stream, changed recording, false or missing non-focus playback
observation, and wrong entry point. Version 2 remains unqualified until all four
Windows profiles are independently audited; it does not replace the version 1
lock, tag or assets.

This additional reference fixture measures four complete unchanged stock scenes
that use the configuration-defined `ISS` class. `DG dumbbell` also contains three
original `Module1` vessels. Every declared vessel remains present. No native
class is admitted by adding this fixture.

The original Windows application, SDK and graphics client remain at
`f725194209634f7fd5d1d44d426cfa9b5e303e37`. Only the already established read-only
public SDK observer is rebuilt. The existing 60-frame, 0.25-second clock,
numerical budgets and full-frame image threshold remain unchanged. Each scene
runs twice in each Debug/Release automatic/SSE2 profile. Captures retain all
61 finalized states for every vessel and every docking port, capability data,
actual loaded modules and math implementation, camera, full framebuffer and
normal graphics teardown.

The scenario, ISS/Module1 configuration and mesh hashes are checked against the
original source. The staged raw scenario hash is recorded before execution and
rechecked alongside its frozen LF identity. The entire preserved package and
observer sources must remain unchanged. Capture jobs alone do not qualify a
native capability policy or complete Phase 6.

The version 1 four-profile measurement audit at observer producer
`e81279b9ca108b27b56925bfe034141416f20f1d` passed the initial measurement audit: 32
processes, 1,920 presentations, 14,640 vessel rows and 25,864 docking-port rows.
All Debug/Release state errors are zero; repeat and paired camera records are
byte-identical and the original full-frame comparison scores are 1.0. The
auditor binds every extracted file to its downloaded ZIP, checks all preserved
SDK/client files against independently retained packages, and verifies actual
MSVC build configuration, CRT linkage, math selection and loaded DLLs.

`observations.lock.json` pins those exact archives, source, metadata and observed
ISS/Module1 capabilities and local docking geometry. It never refreshes a
reference automatically. `frozen_original.py` stages those bytes and replays
the complete audit; a same-size corrupted cache must fail before producing an
audit. `preserve_original.py` publishes only the four already audited original
ZIPs, re-downloads their remote bytes before publication, and never moves a tag
or overwrites an asset. Native qualification requires corrected playback inputs,
matching native runs and clean docked-structure teardown.

`Gate.Test.py` uses the complete dumbbell capture, including all three Module1
objects, to reject twelve damaged copies. Missing background objects, ports or
ticks, duplicate ports, altered capabilities, nonfinite state, shifted time,
changed scenario bytes or line endings, incomplete teardown and a wrong renderer
must fail while the original remains unchanged.
`AuditIdentity.Test.py` additionally checks eight forged archive, producer,
build, reported/raw math, actual launch argument and loaded-application identities.

```sh
python3 -B Tests/Production/LegacyStations/original.py --verify-inputs
```

Actual captures require native Windows/MSVC and the preserved SDK/runtime staged
by `CockpitControls/prepare.py`. Use fresh outputs; never rebuild an accepted
application or SDK to produce a new reference.
