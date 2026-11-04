# Explicit repaired original Windows reference candidate

This is a separately versioned candidate, not an untouched-original reference,
an observations lock, native class admission or Phase 6 acceptance. The failed
original campaigns remain failed and unchanged.

The shared passive SDK observer additionally writes `stock-clock.csv` at the
same initial and finalized boundaries as the vessel snapshots. Its separately
identified `remaining-stock-sdk-clock-v1` samples record system time/step,
simulation time/step and time acceleration using public getters only. They
supply no clock input, change no warp or script ordering, and do not replace or
relax the existing fixed-step, repeat, finalized-frame or complete-scene gates.
The reader checks complete ordered samples, finite values, forward system time
and association with every vessel snapshot; it makes no matched-clock claim.
`RemainingStock/Clock.Test.py` uses real observations and requires eight damaged
copies to fail while leaving the owning evidence unchanged. Both successful and
failed Windows runs retain the raw CSV through the existing artifact rule.

This observation is needed because the original application measures elapsed
system time (capped at 0.1 seconds after three 0.01-second launch steps), while
the current fixed-frame native diagnostic supplies 1/64 second to its system
clock helper. The 120-ms observer delay is not itself a system-clock input in
that native loop. Original scripts that wait on system time can therefore reach
warp changes at different physical ticks. Existing failed clock/repeat captures
remain failures; a matched capture protocol still needs its own evidence and
explicit versioning before it can replace any reference.

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
Twenty damaged real-capture controls check the reader; the existing independent
resource-history controls retain live/retired ownership validation.

`data_inputs.py` hashes the actual 21 kernel files, eight gravity models and 28
standard planet archives before and after the complete campaign. It also hashes
all 57 files in each executed scene after that process exits. Each scene's
`actual-data-inputs.json` retains the sizes, SHA-256 values and original lock
identities; the complete source and scene byte maps must agree. These checks
stream the large archives and do not change the simulation or its inputs. Two
additional scene controls reject a changed data hash or omitted planet archive.

Fresh captures, independent transport/build/profile/state/camera/full-frame audit,
new negative-control results and matched native runs are pending. No failed
original result is reclassified, and no reference is accepted automatically.

`audit.py` requires the exact four artifact ZIPs and their complete decoded trees,
independently retained Debug/Release original packages, the independently retained
pinned Mesa DLLs and an immutable full producer commit. It reconstructs the runtime
file map from actual original and replacement bytes, checks the complete original
SDK, module exports, generated observer, actual MSVC compile commands/CRT and
source closure, then re-reads all 304 actual processes. Windows system DLL paths
and hashes remain explicitly identified as captured process evidence; they are
not confused with replacement DLLs or represented as independently archived bytes.

Every repeated state/resource/playback/mesh/camera trace must be byte-identical.
Both Debug/Release pairs must satisfy the unchanged state and camera budgets and
the original full-frame SSIM minimum. Additional resource numeric differences are
reported as calibration, without inventing acceptance tolerances. A missing or
failed profile produces a retained failed audit. The auditor creates no accepted
reference or class admission.

The transport manifest has `status: "passed"`, the exact `source_commit`, and four
`artifacts` entries with `profile`, `name`, repository-relative ZIP `path`, `bytes`
and `sha256`. Each artifact's decoded directory is `<artifacts>/<profile>/`.

```sh
python3 -B Tests/Production/RemainingStockRepaired/audit.py \
  --artifacts out/repaired-reference-artifacts \
  --download-manifest out/repaired-reference-downloads.json \
  --preserved-debug out/phase6-shuttle-a-preserved-Debug \
  --preserved-release out/phase6-shuttle-a-preserved-Release \
  --mesa-runtime out/mesa-python-stage \
  --producer-commit <full-40-character-capture-producer> \
  --output out/repaired-reference-independent-audit.json
```

`Audit.Test.py` has 18 independent source, compiler, actual loaded-DLL/provider,
data and incomplete-matrix controls. The initial control run is retained at
`out/phase6-repaired-reference-independent-controls-v2.json`. It independently
verified the real failed Debug artifact from `2ddb6ef6ff52f09f25cfc5872dea63197a2afad4`
(140 original / 142 staged source/resource files, exactly five declared changes,
131 compile inputs and 33 client C++ inputs), the separate actual original scene
observer, 91 captured system providers and all 57 actual locked data files.
Damaged copies were rejected and owning evidence remained unchanged. This tests
the sub-readers and proves that the actual failed build and single artifact cannot
qualify; it is not a successful complete repaired-matrix audit. The 20 Windows
scene controls still require fresh complete repaired observations.

The initial candidate workflow
[41774454528](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41774454528)
at `df8f1e0d4e0c7eb8e9da1c2a8ffebde30eb7dfcb` stopped during CMake configuration
in all four profiles: native backslashes in the newly supplied source path were
parsed as CMake escapes. No simulation ran. The hash-verified Debug artifact and
all decoded members remain in
`out/phase6-repaired-reference-configure-failure-df8-v1`. The wrapper now normalizes
all three incoming paths before constructing target sources and exposes failed
build-log tails directly in the job log. A fresh run is required.

The next run
[41774907247](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41774907247)
at `1d1f80b64d70d1ed737d56b788c1381c18b9039a` configured successfully, then the
import-only SRB link failed because the wrapper omitted the original target's
`Common.cpp`, which defines `srb_contrail` and `srb_exhaust`. Both unchanged
original source files are now listed, matching the original SRB target. No
simulation or reference acceptance occurred in that attempt.

At `2ddb6ef6ff52f09f25cfc5872dea63197a2afad4`, workflow
[41775935303](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41775935303),
both Release profiles built successfully and began the full scene campaign.
Both Debug profiles compiled and linked every target, passed original/repaired
module export checks, then stopped at the runtime file guard because MSVC also
emitted four `.ilk` files. The exact hash-verified Debug SSE2 artifact, all decoded
members and compiler inputs remain in
`out/phase6-repaired-reference-runtime-guard-failure-2ddb-v1`. The guard now names
only those four incremental-link files alongside the four existing PDB paths;
all executable/SDK/other-module protections remain strict. Each fresh completed
build must also reject six damaged manifest controls protecting the original
application, SDK, SRB, configuration and unrelated module/root DLL paths.

```sh
python3 -B Tests/Production/RemainingStockRepaired/capture.py --verify-inputs
```
