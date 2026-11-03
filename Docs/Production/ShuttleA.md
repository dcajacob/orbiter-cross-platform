# Shuttle-A local integration qualification

Phase 6 now compiles the original Shuttle-A production module and its payload
in the native cockpit build. Its comparison candidate now admits only the
initial capabilities observed in all four audited Windows profiles. Required
modules still use the checked loader. Local Release automatic state/image
qualification now passes for all six complete Shuttle-A scenes and four complete
DG scenes containing Shuttle-A. Other profiles, interactive acceptance and the
complete admitted stock corpus remain open; Phase 6 is not complete.

The port retains the original flight and parachute calculations, resources,
animations, panel/VC instruments, attachment logic and Lua methods. The source
audit compares all 40 original implementation/header files against preserved
revision `f725194209634f7fd5d1d44d426cfa9b5e303e37`. Windows keeps its SDK
types/layouts and scenario-editor page. Native loading uses the existing checked
module ABI, with one shared drawing-resource lifetime across simultaneous ships.
The native SDK build identity includes the module sources, common instruments
and source mesh used to generate group IDs.

Native SDK adapters delegate rectangular colour fills, mesh-group insertion,
surface/texture loading and legacy panel redraw requests to the existing
production renderer and Pane implementations. Native VC bitmap resources load
the original BMP bytes from staged files. Packed RGB constants have the same
values as the original Windows macro. The Lua declaration linkage is made
consistent with its existing static definitions; method bodies are unchanged.

The new Windows observation matrix covers all six unchanged Shuttle-A scenes
and four complete DG scenes containing Shuttle-A. It preserves every declared
ship, repeats each session, records all vessel states/capabilities and docking
ports, and keeps the existing numerical and image budgets. It builds only an
observer against the preserved application, SDK and graphics client. The four
original Debug/Release automatic/SSE2 profiles must be captured and audited
before admitting native capabilities.

See [the fixture and commands](../../Tests/Production/ShuttleA/README.md).
Other native profiles, interactive Shuttle-A controls, payload deployment and
Shuttle-A flight/cockpit lifetime checks remain pending. The Windows-specific
Shuttle-A scenario-editor page also needs a native UI implementation.

Local integration checks now pass for the compiled candidate `778b6c58`:
14 existing station sessions match the original Windows state/image captures,
with 840 presentations and unchanged budgets. The updated observer also
re-audits all 56 original station sessions successfully. This protects the
existing integration scope while Shuttle-A qualification is pending.

Sanitizers then exposed a startup leak in four payload scenes: each retains
six parent-name strings, totalling 36 bytes, when rejection occurs before
post-creation. Cleanup revision `2d9367c5` adds two destructor lines to release
those pending names. The normal attachment initialization still consumes and
clears them as before. No calculation, callback order or header layout changes.
Source controls reject removal of the cleanup and an incorrect scalar delete.

Fresh Release and sanitizer builds pass. All ten unchanged candidate scenes
now reach the closed capability gate, exit with code 1 and delete their graphics
contexts with zero sanitizer findings. They remain failed stock scenarios.
The cleanup revision also passes eight original Windows flight comparisons
in the established ShuttlePB docking, approach, attachment and lifetime fixtures,
plus twenty sessions and
1,200 presentations with clean sanitizer exits and identical states. Actual
Fontconfig and GDK candidate mappings are retained for all nine processes.
The pinned Mesa candidate was requested in the invocation; the early mapping
snapshots do not prove the later driver mappings.

The [machine-readable checkpoint](ShuttleAStartupVerification.json) records
these scopes and their hashes. The verified local evidence archive is
`out/phase6-shuttle-a-initial-evidence-v1.tar.gz`: 121,654,119 bytes,
3,206 members, SHA-256
`98ea203c928212754b908d59d39aa282a1ae6b54505dc8c24cd21b68c67002a0`.
It retains both runtimes, the four leak cases, clean targeted captures, original
comparisons, source controls and replay recipes. Remote preservation remains
open. All four original Windows Shuttle-A profiles are now downloaded, hash-verified
and audited: 80 sessions, 4,800 presentations and 38,552 finalized all-vessel samples.
Their complete traces, deterministic repeats and Debug/Release pairs pass the
unchanged budgets. Native Shuttle-A state/image qualification is still pending.
The subsequent complete instrumented sweep on cleanup revision `2d9367c5`
is audited: all 157 scenarios were attempted, with 44 passed, 113 failed, no
signal-terminated processes and no sanitizer findings. Its inventory finds
119 complete dependency sets; the capability gate was still closed for that
capture. Every failure and the seven frozen inventory metadata discrepancies
remain recorded. This is an audited incomplete corpus, not full stock acceptance.

The new admission candidate checks SDK version, mesh/thruster/propellant counts,
docking and attachment counts, focus eligibility, transponder, size, inertia
and cross sections against the observed original classes. Shuttle-A payload
mass remains the original scenario-controlled quantity. Only the observed
initial one-mesh cargo configuration is admitted; restored deployed-parachute
configurations still need their own original observations. None of the flight,
parachute or attachment calculations are changed by this policy.

The [native qualification record](ShuttleANativeVerification.json) identifies
runtime code `09eeed20`. All twenty sessions pass against the matching audited
Windows profile: every vessel, capability and docking-port row, the camera and
unmasked full framebuffer. All twenty images are byte-identical to Windows
(SSIM 1.0), with numerical differences below the unchanged budgets. The same ten
unchanged scenes also complete 600 presentations with the engine and renderer
instrumented, normal context deletion and zero sanitizer findings.

Those full graphs exposed two integration defects. A docked DG teardown called
redraw after the cockpit was released. Two native guards had replaced the
original nullable pointer test with a throwing lookup; restoring nullable tests
preserves the original shutdown and callback order. Separately, appending to an
empty CPU mesh group lost its owned zero-length arrays. Releasing the old arrays
outside the nonempty-copy condition leaves all geometry and index calculations
unchanged. The real mesh regression reports 32 leaked allocations before the
fix and zero afterward, with exact geometry/index checks. Both failed baselines
and the first-exception backtrace are retained.

Eight real startup controls reject missing required modules, foreign factories,
generic fallbacks and class clones before presentation, with protected source
configs unchanged. The workflow now captures and compares all four native
build/CPU profiles against pinned original observations without refreshing them.
Hosted results remain pending. A fresh full admitted-corpus run is separate;
the earlier 44/113 result is retained as the closed-gate baseline.

Three further verified local bundles preserve the evidence:

- Native qualification and retained defect baselines: 215,020,944 bytes,
  3,231 members; SHA-256
  `ffd8ac8c764c81a132a2599b0938210a02b1e876b6f2c2e5293d75dc9e16f5d3`.
- Original observations and preserved application/client/SDK code: 169,802,632
  bytes, 357 members; SHA-256
  `54c4a038d8f54aced333c7a7b6fb39606d0f4b0db016e2bcea037a836fea8b41`.
- Complete closed-gate corpus: 5,153,898 bytes, 4,258 members; SHA-256
  `ac2e00b1fd05fc1ae5e59cb4b1013ada89a3ca59122a6f35976375f8cfe527c1`.

Their paths and full indexes are recorded by the machine-readable qualification.
They exclude asset/font collections. Remote preservation remains open.

A separate [keyboard and persistence fixture](../../Tests/Production/ShuttleA/Controls/README.md)
now operates the docking hatch, both airlocks and landing gear in the complete
six-vessel ISS Approach scene. It uses ordinary buffered keys, including F8 to
select the VC. Sixteen local Release automatic sessions pass with 912 presents
and 5,568 finalized all-vessel rows. Both cockpit repetitions have exact state
traces and byte-identical repeated complete frames. Fresh processes restore
moving mechanisms, finish their motion without further input, return them to
their original endpoints and restore those endpoints again. The exact observer
sources are retained alongside this preliminary capture in
`out/phase6-shuttle-a-controls-native-v2/observer-source`.

Five negative controls reject a missing background station, missing attachment
port, missing animation sample, wrong cockpit and forged saved position, with
the original capture unchanged. The dedicated Windows workflow collects all
four original build/CRT profiles with the preserved application, SDK and client.
All four original profiles and their artifact audit now pass. All four native
Debug/Release automatic/SSE2 profiles also pass the controls comparison:
64 sessions, 3,648 presents and 22,272 finalized all-vessel rows. All 32 compared
complete frames are byte-identical to Windows. The new fixture does not qualify
mouse operation, pod controls,
parachute deployment, the editor or overall Phase 6 acceptance.

The observer sources matching pushed commit `8c5b87fb` also pass all sixteen
sessions with the engine, renderer and observer instrumented: 912 presents,
5,568 all-vessel rows, normal context deletion and zero ASan/UBSan/LSan findings.
Actual Fontconfig, Mesa EGL and GDK candidate mappings are verified in every
process. Both cockpit repetitions have exact state traces and byte-identical
repeated full frames. The first instrumented observer incorrectly passed its
preload to GTK's sandboxed image helper; limiting the test preload to the
observed process preserves the loaded instrumentation and normal helper startup.
The failed baseline is retained. Production binaries are unchanged.

The instrumented capture's runner incorrectly labeled its configuration as
Release. Both retained CMake caches prove it is Debug automatic. Its clean
sanitizer and behavior results are retained as smoke evidence and cannot qualify
Release parity. The capture helper now checks the actual build type and SSE2
selection before starting any native session; comparisons also verify every
recorded runtime binary and the build identity.

The [controls verification record](ShuttleAControlsVerification.json) identifies
the captures and open gates. Its verified local evidence archive contains
41,821,515 bytes and 1,456 members, SHA-256
`cb76a3a6a12be7a0c1874b329fd95ff6d505b916cc570a8458e3940e742676fe`.
It includes raw captures, observer sources and replay recipes, and refers to the
previous archive for the matching retained runtime binaries. Asset/font
collections are excluded. Remote preservation remains pending.

The four original controls profiles are now pinned at producer `8c5b87fb`:
64 sessions and 3,648 presents. Offline staging re-audits all four archives,
including exact mechanism/attachment trajectories, all-vessel numerical budgets,
repeated frames and Debug/Release pairs. A corrupted cached archive is rejected
before an audit can be created. Their verified local evidence bundle is
`out/phase6-shuttle-a-controls-original-evidence-v1.tar.gz`: 75,322,330 bytes,
26 members, SHA-256
`5630c5c49f6c0dd99118b1eac7c119f81bdc218049aaf442215215be036427df`.

The [admitted-corpus audit](ShuttleAAdmittedCorpusVerification.json) now covers
all 157 unchanged scenes: 112 passed and 45 failed. The first controller reached
its 1,800-second limit after 149 completed attempts; a separate invocation ran
exactly the eight remaining cases with unchanged binaries and source. The
derived manifest retains every completed raw result and records its origin.
The independent verifier rechecks all 157 cases. There are no signal-terminated
scenario processes, 119 complete dependency inventories and seven frozen
metadata discrepancies.

That historical sweep records two sanitizer diagnostics: Transfer MFD reads its uninitialized
`dv_manip` boolean when a hypothetical orbit is restored; the unchanged vessel
API script passes its assertions and then calls `oapi.exit(0)`, skipping normal
graphics teardown and leaving 15,264 bytes in 76 EGL allocations. Four other
inventory-ready failures reject unqualified legacy ISS capabilities, and the
original GeneralApiTest assertion remains failed. The other 38 failures have
incomplete dependencies. These results preserve the full acceptance scope.

The [Transfer MFD follow-up](TransferMfd.md) repairs initialization, a rotation
matrix lifetime and nonfinite indicator conversion. Both unchanged lunar-transfer
scenes now pass baseline, repaired Release and repaired instrumented Debug runs:
six clean process exits and 360 presents, with byte-identical all-vessel physical
states against the retained native baseline. The historical 112/45 corpus result
is retained; the Lua explicit-exit cleanup defect remains open.

The verified local admitted-corpus bundle contains 34,805,441 bytes and 8,522
members, SHA-256
`5142eee73ef1f98d08ca18a8c5184b5d2d9303ecf1d919fa8fe5dcb2ce3d28b9`.
It retains both source captures, the derived provenance, failed cases and
independent audit, with replay recipes and the matching runtime archive
reference. Asset/font collections are excluded; remote preservation remains open.

The corrected controls comparisons verify actual CRT math selection for every
session, the recorded observer's immutable producer source, every runtime
binary and the actual build configuration. Separate copied-report controls
reject forged math/source identities and retain the original capture unchanged.
The hosted four-profile workflow now runs these controls and persistence cases
alongside the initial-scene comparison, using the pinned originals.

The [durable original-controls release](https://github.com/dcajacob/orbiter-cross-platform/releases/tag/phase6-shuttle-a-controls-original-v1)
now preserves all four pinned ZIPs. The workflow verifies their remote bytes
before publication; independent anonymous downloads match all four hashes,
and a fresh tokenless helper invocation re-audits all 64 sessions. Release asset
identities are pinned without replacing the original observations. Other local
evidence bundles still need remote preservation.

The verified four-profile native controls bundle is
`out/phase6-shuttle-a-controls-parity-evidence-v2.tar.gz`: 127,632,041 bytes,
2,781 members, SHA-256
`4ed09506fc0a9ae214a4e4685ecf7720343e38ae5be92d0b8261db62b7627233`.
It retains all 64 native captures, comparisons, source snapshots, identity
controls, the failed desktop-GVFS startup, three fresh coherent runtimes and
build logs. It references the existing bundle for the retained Release automatic
runtime. A private D-Bus session resolves the startup timeout. Asset/font
collections are excluded.
