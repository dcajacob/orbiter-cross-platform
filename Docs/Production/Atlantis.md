# Native Atlantis integration candidate

The original Atlantis orbiter, external tank and solid rocket boosters now compile
and link as three native modules. This is a source integration candidate. Matched
runtime, lifetime and interaction qualification remains pending; the production
class capability gate still requires qualification before admission. The complete
stock sweep remains at 118 passes and 39 failures.

`Tests/Production/Atlantis/source_audit.py` conserves all eleven original Atlantis
source/header files at `f725194209634f7fd5d1d44d426cfa9b5e303e37`: nine runtime
files and two unchanged Windows configuration-tool files. It also checks all
nine original meshes/class configurations. The port uses explicit SDK scalar,
message, rectangle and text adapters, existing native UI services, and checked
native factory entry points. Each class retains its own checked SDK bootstrap module. Their original C++
implementations share a private library, so the tank's checked Atlantis casts
resolve the orbiter's real RTTI under UBSan without a circular library dependency.

The payload-bay UI and ascent autopilot retain their original ImGui and ImPlot
implementations. The native cockpit now owns the same ImPlot creation/destruction
order as the original application. ImPlot is pinned to the original commit
`3da8bd34299965d3b0ab124df743fe3e076fa222`; its exact archive hash is in
`Tests/Production/Atlantis/dependencies.lock.json` and its MIT notice accompanies native modules. The
existing audited notice in `Tests/Production/Licenses/implot-LICENSE` matches the
downloaded source. Offline builds can set `ORBITER_NATIVE_PLOT_ARCHIVE`.

The original grapple-visibility setter, surface-size graphics callback, surface
Image wrapper, and `sscan_state`/`WriteScenario_state` bodies now serve the native
module. The source audit verifies those bodies against the preserved original,
with only explicit context, export and fixed-width bindings.

The prototype Release build at
`out/phase6-atlantis-candidate-Release-v1-engine` passes compilation and linkage
with no undefined symbols. Its three exported factories and initial shared-library
dependencies were inspected; the report is
`out/phase6-atlantis-candidate-Release-v1-build/verification.json`.
Initial compile/link failures remain in that build's separate attempt logs.
This prototype has not supplied runtime acceptance evidence. A fresh normal
package compiled successfully; the first sanitizer link exposed the cross-library
RTTI dependency described above. Failed build reports and separate attempt logs
remain retained, including a source-guard key-set bookkeeping failure and a
ptrace-incompatible sanitizer mesh-compiler launch. Fresh qualified builds must
check the full owning-source and dependency input sets outside ptrace.

The [complete remaining-stock Windows reference](../../Tests/Production/RemainingStock/README.md)
is measuring all 38 unchanged complete scenes in four profiles. Its corrected
run is [41752276001](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41752276001),
producer `da11decc84db1211bd2efc016594880f8d5cc269`. All four profiles had reached
capture when this candidate was prepared. The earlier failed attempt is retained.

The earlier full hosted comparison matrix at
`99f407569ca0d827b1645008ddf71a0bb4e45824` has finished with all sixteen jobs
successful: four Windows observation jobs, four native jobs and eight matched
spacecraft/Shuttle-A comparison jobs in
[41735121120](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41735121120).
That result belongs to its recorded source; fresh current-source checks remain
required.

Remaining Atlantis work includes complete original/native scene state, generated
vessels, attachments, tank ownership, docks, camera and full-frame comparisons;
orbiter/booster/tank cleanup under sanitizers; physical cockpit and payload-bay,
RMS, ascent-MFD/autopilot controls; save/reload; rejection controls; and the current
four-profile hosted matrix. The wider Phase 6 module, hardware, input and
performance gates remain open, including the unavailable physical controller.

`Tests/Production/Atlantis/stage_assets.py` extends a retained native resource
tree with all remaining vessel families at their original installed paths. The
staged tree verifies 38 complete scenes, 19 class configurations and all 36
recording files, preserves the original final stock-data texture overlay, and
checks that its base remains unchanged. Local output
`out/phase6-remaining-vessels-resources-v2` contains 1,102 files with 79 vessel
resource entries. Asset availability remains separate from implementation and
runtime qualification.

The shared-implementation sanitizer prototype now links successfully.
`Tests/Production/Atlantis/Bootstrap.Test.cpp` completed 60 real module
load/version/identity/missing-host/unload cycles with ASan/UBSan, leak detection
and no suppressions. The exact local invocation and result are retained in
`out/phase6-atlantis-shared-runtime-bootstrap-v1/verification.json`. This probes
SDK library lifetime and does not instantiate a vessel or qualify simulation.

The fresh `1052e1a7cf9ffdaafd262f1355e3e409b9f6934c` Release and Debug
ASan/UBSan packages completed all 505 owning-source/dependency checks. The
unchanged “DG Mk4 in orbit” scene then completed 60 real native frames with
clean sanitizer teardown; evidence and a 2D-cockpit screenshot are in
`out/phase6-progress-2d-source-port-v1`. This is a DG regression, not Atlantis
simulation qualification.

Actual construction of the unchanged Atlantis-only Edwards approach scene
exposed an inherited `new-delete-type-mismatch`: `Atlantis::~Atlantis` deleted
an 88-byte RMS `MGROUP_ROTATE` through its 32-byte non-virtual base. The failed
run, stack, exact invocation and unchanged assets remain in
`out/phase6-atlantis-construction-diagnostic-v1`. The six RMS allocations now
use their allocated type during deletion; source conservation allows only that
confirmed cleanup correction. A fresh instrumented rerun remains required to
inspect the rest of teardown.

The first fresh typed-deletion rerun reached the still-closed Atlantis capability
gate and deleted the graphics context, then LSan reported 473 bytes in six
allocations. `out/phase6-atlantis-construction-diagnostic-v2/leak-audit.json`
binds the actual library and console bytes and resolves the three SSME rotation
allocations to `DefineAnimations`; the remaining owners are the module font and
brush plus the font's stored name. The three SSME rotations now use their
allocated type during vessel destruction, and module drawing-resource release
frees its font/brush and clears their handles. A fresh fully enabled sanitizer
rerun must verify the combined cleanup before any runtime admission.

The combined cleanup passes the fresh `056f20c1a2d717d84c18a14d72ae622657b99901`
Debug ASan/UBSan package: the real unchanged Edwards approach scene constructs
Atlantis, reaches the production capability gate, and tears down its graphics
context with zero sanitizer diagnostics.
`out/phase6-atlantis-construction-diagnostic-v3/verification.json` records the
result. This is a clean rejected construction, with zero presentations; simulation
and class admission remain unqualified.

All four remaining-stock reference profiles at `da11decc` are now terminal
failures. Their exact ZIPs, decoded members and observer source snapshots are
retained in `out/phase6-remaining-stock-original-failed-v2`; the independent audit
is `out/phase6-remaining-stock-original-failure-audit-v2.json`. Profile-local
capture checks completed for 28/28/28/30 scenes, but no full reference profile
qualifies. Debug fuel observations become invalid after an external tank leaves
the population; Release repeats diverge (mostly fuel, with broader later state
divergence in one scene). The ascent demo times out. Four Dragonfly cockpit scenes
report invalid surface dimensions and, in Release, further OpenGL diagnostics.
No numerical or image budget has been changed to admit these failures.

An optional, uninstalled `production_atlantis_diagnostic` executable now permits
the real Atlantis/tank/SRB structural capabilities for isolated defect
reproduction. It compiles the same native host/session/rendering code, retains
checked source-built modules, emits `unqualified-atlantis-diagnostic.json`, and
keeps production admission unchanged. Build with
`ORBITER_BUILD_ATLANTIS_DIAGNOSTIC=ON` only for this test host. Its executable is
not a qualifying production runtime or a substitute for complete reference,
scenario, interaction and hardware gates.

The isolated `003c10e41ae1effe4d14387d9d8ad0dd918ced35` diagnostic has now
reproduced a heap-use-after-free in the unchanged complete KSC tour. ASan traces
the invalid `VESSEL::GetFuelMass()` read to the external tank's freed propellant
resource. The failed invocation, source/dependency identities, complete console
and unchanged assets are retained in `out/phase6-atlantis-pad-lifetime-v1`.
The original tank post-step callback deletes itself below ground even while
port 0 remains connected to the orbiter, which still uses its propellant.
The callback now permits that deletion only after the orbiter port is undocked;
the original altitude condition and deletion service remain unchanged. This is
an explicit lifetime correction in the source audit, applied on both platforms.
Fresh instrumented execution and detached-tank deletion controls remain required.
Any repaired Windows comparison must use an explicitly versioned source variant;
the failed unmodified original captures remain preserved.

The fresh `3aa99da724f711b6775a9fa56b0d508d7818f017` Debug ASan/UBSan
package completes the unchanged KSC tour with the complete five-vessel launch
stack retained through 61 finalized ticks and 60 presentations. The actual
post-step witness observes the tank below ground while still connected. Two
supplemental controls verify that an undocked below-ground tank is deleted after
its first callback, while an undocked above-ground tank survives all 60 callbacks.
All three processes have clean sanitizer teardown, with all 505 source/dependency
inputs, 1,102 assets, binaries and verifier bytes unchanged. The local result is
`out/phase6-atlantis-tank-lifetime-v5/verification.json`; the reusable runner is
`Tests/Production/Atlantis/tank_lifetime.py`. Its read-only callback probe retains
the implementation's local loader scope and forwards every original argument.
Earlier failed control/observer attempts and their verifier snapshots remain
retained. The unchanged Edwards approach also completes 60 clean native frames;
its actual approach-view screenshot is in `out/phase6-progress-atlantis-edwards-v1`.
These are isolated lifetime and smoke results. The KSC ground-contact trajectory
still grows to extreme numerical magnitudes; finite state and clean memory do
not establish valid dynamics or qualify the stock scene.

Hosted checks at `003c10e4` and `3aa99da7` exposed a separate frozen-reference
input mismatch: adding ImPlot to the shared renderer dependency lock invalidated
its recorded input hash. The renderer lock now returns to its exact frozen bytes,
and the same ImPlot pin lives in the dedicated native Atlantis lock, which the
native SDK source fingerprint includes. Frozen reference provenance, binaries,
captures and comparison budgets remain unchanged. Fresh hosted checks are required
after this lock-layout correction.

The fresh corrected-lock package at
`5e1ff0625e011eddcc642789164c494af081cc18` repeats all three real lifetime
cases successfully. `out/phase6-atlantis-tank-lifetime-v6/verification.json`
records 180 presentations, three clean graphics-context deletions, 506 guarded
source/dependency inputs, 1,102 unchanged assets and the immutable 20-file observer
source closure. Callback clocks are checked at every quarter-second boundary.
The frozen Windows cockpit metadata/source audit also passes again without
changing its provenance or comparison budgets. The independent earlier lifetime
audit is `out/phase6-atlantis-lifetime-audit-v1.json`; it explicitly records the
unqualified KSC trajectory's extreme position/speed magnitudes alongside the
successful memory-lifetime observations.

A configuration-only diagnostic at the same `5e1ff062` runtime has isolated a
cause of the extreme KSC trajectory. With the existing reference's forced
single-step propagator settings, the tank reaches approximately `6.20e70` metres
geocentric distance in 15 seconds. Removing only the three propagator overrides
lets the original production defaults select their integration method and
substeps: maximum tank distance is about `6.372e6` metres and speed about
`421.1 m/s` over the same interval. Both runs retain all 60 actual frames, the
unchanged complete stock scene, identical original algorithms, all 506 owning
inputs and all assets, and clean sanitizer teardown. Raw inputs and observations
are in `out/phase6-atlantis-propagation-diagnostic-v1`. This identifies a fixture
configuration problem; it does not establish complete mission stability or
Windows/native parity. Existing captures, protocol settings and budgets remain
untouched. A separately versioned comparison using original production default
propagation remains required.

At owning source `4b03aa4dd60a778b9f2bc43d3f9ccb8745e3d7f1`, the fresh
Debug ASan/UBSan package repeats all three actual tank lifetime cases cleanly in
`out/phase6-atlantis-tank-lifetime-v9`: 180 presents, three clean context
deletions, 510 unchanged owning/dependency inputs and 1,102 unchanged assets.
This execution selects the source-pinned GTK icon-owner candidate described in
`WindowingLifetime.md`. Production admission remains closed.

Two complete unchanged KSC diagnostics now use the original production
propagator defaults over 15 simulated seconds: 900 actual 60-Hz frames and 960
actual 64-Hz frames. Both have clean ASan/UBSan/LSan and GL teardown. The tank's
mean altitude stays between 65.9769 and 65.9782 metres in both runs; the complete
five-vessel population remains present. The 64-Hz finalized simulation clock is
binary-exact. Raw observations and actual screenshots are retained in
`out/phase6-atlantis-propagation-{60,64}hz-v1`; the independent whole-population,
source/asset/runtime/loaded-plugin/clock audit is
`out/phase6-atlantis-default-propagation-audit-v3.json`. It checks 9,310 actual
vessel-state rows and all 510 owning/dependency inputs and 1,102 assets.

Cross-rate diagnostics record a maximum 0.002119-metre position difference,
0.002163-metre/second velocity difference and full-frame SSIM 0.984812. These are
calibration measurements. Qualifying Windows/native comparisons still require
the same step and unchanged state/camera/image budgets.
`Tests/Production/RemainingStockRepaired/protocol.json` explicitly versions a
960-tick, 1/64-second, original-default-propagator candidate, retaining the same
15-second interval and 12.5-second full-frame capture time. Its four-profile
Windows campaign keeps all 38 complete scenes and both repetitions, with explicit
tank/Dragonfly/client replacements in a fresh copy of the original application
and SDK. No observations lock or full stock admission follows automatically.
