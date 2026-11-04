# Original legacy station observations

The corrected version 2 reference and all five matching native packages pass the
state, docking-port, camera, projected-landmark and full-frame gates for these
four unchanged complete scenes: `Smack!`, `Vessel-vessel`, `DG dumbbell` and
`Smack! Rescue`. Each run observes every declared vessel for 60 fixed quarter-
second frames (15 simulated seconds). This does not qualify the entire nine-
minute tutorial or complete Phase 6.

Application, public SDK and original Windows client remain at
`f725194209634f7fd5d1d44d426cfa9b5e303e37`. Observer producer and tested native
runtime source are `aeee5826eb86c5c64e6c0fc97f40a20f8104459e`. The original
reference contains 32 runs: two repeats of every scene in Debug/Release with
automatic and forced SSE2 math. All four matching native profiles and an extra
Debug ASAN/UBSAN package pass 40 runs and 2,400 completed presentations. Every
full-frame comparison scores 1.0; position, velocity, camera and projected
landmark errors are zero. Rotation and angular-rate errors remain within the
unchanged original budgets.

Version 2 uses `cases-v2.json`, each original relative scenario filename and
Windows-native launch separators in the preserved application. All 22 files in
`Flights/Smack! Rescue` are pinned to the original source. Both observers record
the actual public SDK `Playback()` flag for every vessel at ticks 0 through 60.
All seven rescue vessels must remain in playback; the other scenes must remain
outside playback. Raw pre-execution scenario and recording hashes are rechecked
alongside their frozen LF identities. Preserved application/SDK/client files,
actual MSVC configuration/CRT, loaded modules, math selection, teardown and every
extracted archive byte are independently audited.

`observations-v2.lock.json` pins the four exact v2 archives and measurements.
`frozen_original.py` stages and independently re-audits them without refreshing
any reference. An offline positive replay passes; a same-size corrupted ZIP
fails before creating an audit. `preserve_original.py` publishes only those four
audited archives under the separate v2 tag, verifies the remote bytes, and never
moves a tag or replaces an asset. Public v2 preservation is pending until its
workflow and anonymous replay complete.

`Gate.Test.py` rejects twelve damaged real captures per Windows profile.
`PlaybackGate.Test.py` rejects five missing/changed recording, playback and entry-
point controls per profile. `AuditIdentity.Test.py` rejects eight forged archive,
producer, build, math, launch-argument and loaded-application identities.
`Policy.Test.py` rejects sixteen real invalid factories, class clones, altered
capabilities and docking-port cases on both normal and ASAN/UBSAN packages,
with zero presentations and clean context deletion. Sanitizers use leak detection
without suppressions.

The tested runtime defers dock-port reclamation until every ordered undock and
NAV notification completes. A separate native-only constructor-failure cleanup
frees the default allocations when module loading throws. Successful pre/post
sessions retain byte-identical state, ports, playback flags, camera and complete
frames. Exact source conservation covers all 479 owning files and unchanged
Windows SDK layouts.

**Version 1 limitation:** its rescue fixture used `Behavior.scn` and omitted the
named recordings, so the original silently fell back from playback. The three
non-playback observations remain valid; the rescue case is unqualified. Version
1 bytes, tag and assets remain preserved, and its public release carries this
limitation. `observations.lock.json` retains the limited v1 identities.

The native capability policy admits only the measured literal `ISS` and
`Module1` configuration-defined classes and their exact capabilities/local ports.
Reference pinning alone does not admit a native class. See
[verification](../../../Docs/Production/LegacyStationsVerification.json) and
[scope and remaining gates](../../../Docs/Production/LegacyStations.md).

```sh
python3 -B Tests/Production/LegacyStations/original.py --verify-inputs
```

Use fresh outputs. Never rebuild retained application or SDK packages to produce
new evidence. The 157-scenario corpus, current hosted comparisons, remaining
stock modules/assertion, hardware/input/performance and complete evidence
preservation retain their separate Phase 6 gates.
