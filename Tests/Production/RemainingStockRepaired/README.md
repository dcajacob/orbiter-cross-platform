# Explicit repaired original Windows reference candidate

Source variant v3 additionally initializes the transient `ADI::ref_handle`
request to zero. Actual original-scene allocation controls reproduce the saved
reference difference with no physical-state change or user reference request.
The original constructor leaves that flag undefined; its paint path captures a
reference for any nonzero value. The single assignment preserves loaded manual
references and all original orientation/drawing operations. The independent
reader derives the complete ADI source/header from the frozen original for both
v2 and v3, with exact allowed platform ownership and constructor changes. Missing
or nonzero requests, attitude formula changes, false initialization metadata and
mislabeling v3 as v2 are rejected even with self-consistent damaged manifests.
Fresh v3 Windows execution and full persistence/input qualification remain
required; prior v2 captures and their recorded failures remain unchanged.


This is a separately versioned candidate, not an untouched-original reference,
an observations lock, native class admission or Phase 6 acceptance. The failed
original campaigns remain failed and unchanged.

The original-package auditor verifies every retained original file as raw bytes.
The generated `control-reference-runtime.json` delivery report alone has an
explicit host representation rule: its exact LF and CRLF forms are independently
derived from the retained report. Values, archive identities, ordering and all
other whitespace remain exact. The embedded `test-runtime.json` archive member
and all application/SDK/module/resource bytes retain raw-byte equality.
`OriginalMetadata.Test.py` uses actual retained/delivered metadata, checks both
report forms and rejects eight damaged copies without changing either owning
package. All four capture workflows retain those controls. The independent
auditor requires them when the immutable producer includes that test; it does
not invent missing tests for historical source versions. An actual Windows
artifact exposed the former cross-host report mismatch; its failed audit is
retained beside the corrected independent audit.

## Explicit matched-clock protocol v2

`--protocol remaining-stock-matched-clock-v2` selects the separate
`matched-clock-v2.json` contract in both the Windows builder/capture and native
capture. The default remains `remaining-stock-repaired-v1`; its JSON contract and
the failed historical captures are retained. The full-reference auditor requires
an explicit matching protocol selector, all 38 scenes twice and all four profiles;
it rejects diagnostic subsets. V2 diagnostics do not establish native admission
or an accepted replacement reference.

V2 retains the unchanged complete scenes/scripts, 960 physical steps, original
1/64-second fixed input, original production propagators and all existing state,
camera and image budgets. The native diagnostic alone accepts a bounded
`--fixed-system-step 0.1` input through the original startup/clamp helper, matching
the actual Windows system steps: 0.01 for the first three, then 0.1. The ordinary
native application does not expose that diagnostic argument. Original scripts
retain control of time acceleration; physical steps use their actual warp.

The passive observer now writes `stock-step-clock.csv` immediately after
BeginStep and before module callbacks, in addition to `stock-clock.csv` at the
initial/finalized boundaries. The reader checks actual startup/system inputs,
pre-callback warp, the physical step, the conserved clock accumulator and every
vessel's observed simulation time. A post-step warp change is distinguished
from the warp used by the physical step.

The explicit `remaining-stock-finalized-frame-v2.txt` descriptor selects actual
finalized tick 800 through a private versioned observer getter. Both renderers
read the real framebuffer after world/camera finalization at that tick, and
record the actual simulation time plus protocol/tick in the frame summary.
They reject missing/incompatible observers and skipped ticks. This preserves
the same tick selection when a script crosses the old 12.5-second target in a
larger warped physical step; no interpolation, script override or API value is
substituted. Absent the descriptor, the legacy capture policy remains active.

The separate `Windows Matched-Clock Complete-Scene Diagnostics v2` workflow
runs PoweredUp and Spin stabilisation twice in all four Windows profiles with
an explicit diagnostic-only marker. The builder executes nine standalone
frame-policy damage controls. `MatchedClock.Test.py` requires real captured
begin/end/vessel clocks and frame metadata, rejects fourteen damaged copies and
checks that owning capture bytes remain unchanged. Real execution and a full
independent four-profile/reference audit remain required before qualification.
The separate `Windows Matched-Clock Full Remaining Stock Candidate v2` workflow
runs all 38 complete scenes twice, retains original-runtime/source damage
controls and adds the actual matched-clock controls. `audit.py --protocol
remaining-stock-matched-clock-v2` checks the explicit v2 artifact names, compiled
frame-policy control binary/results, real clock/frame controls and immutable
source/input closure in addition to every existing complete-scene, original
package, module, data, repeat and build-pair gate. It creates no automatic
reference promotion or Phase 6 completion.

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

The separate `Windows Complete-Scene Clock and Initial-Current Diagnostics`
workflow runs complete unchanged PoweredUp and Spin stabilisation scenes twice
in all four Windows profiles, independently of the longer 38-scene campaign.
`capture.py --diagnostic-case` verifies the full frozen 38-scene input inventory
before selecting complete scenes. It records `diagnostic_only: true` and the
requested case IDs in both the campaign and each executed reference variant.
Even a successful selection has status `captured-diagnostic-only`; the independent
full-reference auditor explicitly rejects it. Unknown or duplicate selectors
fail. With no diagnostic selector, all 38 scenes remain required.

Every original fixed-step, finalized-frame, repeat and input gate still runs in
the diagnostic workflow. A system-time script reaching warp and failing the old
frame gate remains a failing diagnostic, with its raw clock/state/log evidence
uploaded. The separate workflow provides earlier owning evidence for the clock
and initialization investigation; it creates no accepted reference or native
class admission. Both workflow files are immutable build/capture source inputs.

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
and resource trees. Source variant v1 changed exactly five paths: the tank
callback, the two ADI source/header files and two new WGL ownership helpers.
Source variant v2 additionally initializes `FCell::Amperes` to zero before its
first thermal read. Independent actual native allocation-pattern controls
reproduce both sides of the inherited Windows tick-2 vent/mass mismatch, and
the failed Windows save contains a nonfinite waste tank. The source auditor
independently derives the sole added electrical assignment from the frozen
original, and `SourceVariant.Test.py` rejects missing/changed initialization,
thermal-formula changes and false policy metadata even with internally
consistent damaged manifests. Every original update formula and callback order
is retained; no old failed capture is accepted. Fresh v2 Windows execution and
full four-profile/native qualification remain required. The original Windows
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
