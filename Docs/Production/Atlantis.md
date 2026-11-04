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
native factory entry points. The original orbiter-to-tank-to-booster C++ library
dependency chain is retained. Each module exports its own checked bootstrap.

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
with no undefined symbols. Its three exported factories and actual shared-library
dependencies were inspected; the report is
`out/phase6-atlantis-candidate-Release-v1-build/verification.json`.
Initial compile/link failures remain in that build's separate attempt logs.
This prototype has not supplied runtime acceptance evidence.

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
