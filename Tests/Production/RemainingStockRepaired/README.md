# Explicit repaired original Windows reference candidate

This is a separately versioned candidate, not an untouched-original reference,
an observations lock, native class admission or Phase 6 acceptance. The failed
original campaigns remain failed and unchanged.

The original v2 campaign at `da11decc84db1211bd2efc016594880f8d5cc269`, workflow
[41752276001](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41752276001),
failed in all four profiles. Its exact ZIPs and decoded members remain under
`out/phase6-remaining-stock-original-failed-v2`; the independent failure audit is
`out/phase6-remaining-stock-original-failure-audit-v2.json`. It exposed connected
tank deletion/stale fuel reads, unstable quarter-second single-step launch
stacks and real Dragonfly GDI/WGL failures after the exact mesh delivery repair.

`build.py` verifies the retained `f725194209634f7fd5d1d44d426cfa9b5e303e37`
application/SDK/client package, copies it to a fresh directory, and replaces only
the connected-lifetime tank module, Dragonfly's ADI context/bitmap implementation,
the current real OpenGL client and the passive observer. The application, public
SDK, actual original SRB and other vessel DLLs remain byte-identical. The current
client uses private `DWORD`/`UINT` aliases with compile-time type assertions;
the retained SDK is never edited. Original and replacement binary hashes, all
compiler inputs, compile commands, CRT configuration, exact source copies and
module export checks are retained. The unchanged SRB is rebuilt solely to obtain
an MSVC import library; that build's DLL never enters the running application.

`prepare_sources.py` stages the complete original Atlantis and Dragonfly source
and resource trees. Exactly five paths differ: the tank callback, the two ADI
source/header files and two new WGL ownership helpers. The original Windows
Atlantis header is retained, including its public and exported class spellings.
Existing source audits preserve every original physics and ADI drawing operation.

The previous fixture forced a single RK4 step for each quarter-second frame.
An isolated unchanged KSC scene reached `6.20e70 m` with that configuration. With
original production propagator defaults and 900 actual 60-Hz frames, the connected
stack remained stable, with 900 presents and clean ASan/UBSan/LSan teardown
(`out/phase6-atlantis-propagation-60hz-v1`). This is diagnostic evidence, not Windows
or native parity qualification.

The new explicit protocol uses the original production propagator defaults and
960 actual 1/64-second frames over the same 15-second observation interval. The
binary-exact step preserves exact finalized clock checks; 12.5 seconds remains
the full-frame capture time, now at tick 800. The observer's sole source change
validates 960 ticks instead of 60; all observation calls, epoch selection and
120-ms per-frame instrument-refresh delay remain unchanged. No force formula,
propagation algorithm, state/camera/image budget or mission input is changed.

All 38 complete unchanged scenes, all 19 class configurations and all 36 existing
recording files remain required. Every vessel, resource, attachment, port,
playback flag and mesh is observed at every actual tick. Both repetitions in all
four Debug/Release automatic/SSE2 profiles are required: 304 processes and 291,840
real presentations. The initial workflow can take several hours per profile.
Loaded modules must match the explicit variant, with no generic vessel fallback.
Eighteen damaged real-capture controls check the reader; the existing independent
resource-history controls retain live/retired ownership validation.

Fresh captures, independent transport/build/profile/state/camera/full-frame audit,
new negative-control results and matched native runs are pending. No failed
original result is reclassified, and no reference is accepted automatically.

The initial candidate workflow
[41774454528](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41774454528)
at `df8f1e0d4e0c7eb8e9da1c2a8ffebde30eb7dfcb` stopped during CMake configuration
in all four profiles: native backslashes in the newly supplied source path were
parsed as CMake escapes. No simulation ran. The hash-verified Debug artifact and
all decoded members remain in
`out/phase6-repaired-reference-configure-failure-df8-v1`. The wrapper now normalizes
all three incoming paths before constructing target sources and exposes failed
build-log tails directly in the job log. A fresh run is required.

```sh
python3 -B Tests/Production/RemainingStockRepaired/capture.py --verify-inputs
```
