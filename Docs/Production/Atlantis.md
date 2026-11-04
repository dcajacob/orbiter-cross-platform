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
`3da8bd34299965d3b0ab124df743fe3e076fa222`; its exact archive hash is in the
OpenGL dependency lock and its MIT notice accompanies native modules. The
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
