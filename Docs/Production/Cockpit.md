# Phase 6 cockpit and instrument integration

Phase 6 is in progress. Phase 5 remains accepted; the prepared laptop preview is
still the verified production ShuttlePB/ISS external-view build. No native
cockpit or Delta-glider capability is claimed by the engineering probes below.

The pre-extraction reference gate is accepted in
[run 41458001638](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41458001638).
All nine cases run twice in both MSVC configurations. All state and projected
overlay differences are zero, displayed text/atlas traces match exactly, and
every image comparison has SSIM 1.0. Both complete Windows builds pass all 22
existing tests. Independent local comparison of hash-verified artifacts agrees.
[Reference provenance and commands](../../Tests/Production/Cockpit/Reference/README.md)
pin the captures and budgets; capture is now manual-only.
The preservation gate publishes exact original archives and binaries in
[release storage](https://github.com/dcajacob/orbiter-cross-platform/releases/tag/production-windows-cockpit-v1)
and verifies a fresh download/staging of the public evidence. Offline staging
and refusal to overwrite a staged reference were also checked locally.
The existing Windows client workflow now recompiles the observation driver
against each current SDK and compares all nine cockpits with that frozen
reference, including 36 actual MFD texture readbacks. The original Debug/Release
MFD texture comparison also has SSIM 1.0 in every image.

Initial diagnostics execute the original Windows application and SDK at
`d14fa7941bd4b60bd5b07c8e444ebfb87761893f`, from Phase 5 run 41396231165.
The current candidate completely rebuilds Windows at
`f725194209634f7fd5d1d44d426cfa9b5e303e37`, with only the pre-reference fuel-display
timer repair described below. Complete application/SDK hashes and matching
owning sources are checked before compiling the SDK-only control driver. Pane,
HUD, stock MFDs, panel and VC code remain unchanged; no extraction has started.

The real Windows OpenGL client receives opt-in text/readback observation hooks.
They record actual Sketchpad calls, original displayed numbers, surface identity,
font height and color, plus complete 1280x720 frames at ticks 20 and 50. They
forward the existing drawing path without replacing instrument calculations or
geometry. The same hooks are available in the shared native renderer but are
disabled for ordinary runs and previous regression fixtures.
Overlay vertices/UVs and self-blits into character atlases are recorded too,
covering HUD numbers drawn with the original bitmap glyph meshes. Glyph/UV and
atlas-update identities must match; projected overlay differences are limited to
one pixel, in addition to the full-image and displayed-text gates.

Nine reduced probes cover all ten stock MFD modes, all three HUD modes, and real
DG/DG-S 2D panels/virtual cockpits. Every probe runs twice with 60 quarter-second
physics steps. The driver paces software rendering by 120 ms per frame so the
unchanged stock 10 Hz wall-time MFD limiter does not discard updates. Simulation
clocks, numerical formulas and the MFD scheduler are unchanged. The FPS, menu and
information bars are hidden; no image masks are used.

`source.lock.json` preserves hashes of 98 original cockpit, instrumentation,
selection and DG/DG-S owning sources. `sources.py --current` verifies they are
unchanged before capture. These source pins are independent of runtime acceptance.

Initial captures are not accepted: a missing direct MSVC include was corrected,
the harness now selects and verifies actual llvmpipe, and cockpit initialization
exposed negative font heights passed unchanged to NanoVG. The shared renderer
now maps negative character heights to positive raster sizes and rejects invalid
surface dimensions without aborting. The packed depth/stencil target is attached
through its matching GL attachment. A separate native renderer probe verifies
actual glyph pixels, sensible negative-height metrics, GL error state and surface
rejection without creating a replacement simulation or instrument. Locally it
reports 9x14 metrics and 271 colored glyph pixels for the `-14` request; the old
preserved renderer fails the same focused exercise. Full Windows cockpit probes
must pass before any capture is frozen or instrumentation extraction starts.
The driver sets instrument modes at the first pre-step: original Orbiter calls
plugin `clbkSimulationStart` before `Pane::InitState`, so that callback is too
early to issue MFD commands. Application lifecycle ordering is unchanged.

Subsequent diagnostic runs completed the generic instrument cases but exposed
blank display copies and compressed stock textures being used as drawing
targets by DG. These are not accepted golden images. Surface copies now disable
depth/stencil testing; overlapping self-copies use a source snapshot. A stock
DDS texture is decoded into the same renderer-owned texture when it first
becomes writable. The focused native probe checks the real compressed ShuttlePB
texture: 300 glyph pixels change and the surrounding pixels remain intact.
Captured MFD textures must contain actual colored drawing and a nonwhite
background, in addition to recording drawing calls. The cockpit harness stages
the original runtime independently of the earlier flight trace validator.
Internal views now check their focus visual on the first render update; the
general round-robin visibility scan previously left DG's cockpit absent for
over forty frames while visiting Sol's bodies. Capture checks require the real
focus visual in the first frame and actual vessel mesh draws for VC cases.
Panel, surface-copy and rectangle-fill vertex buffers belong to the client and
are deleted/reset before its GL context is destroyed. Panel uploads allocate
for the actual group size rather than assuming a 2,048-vertex limit. Rectangle
fills and scaled copies use the same depth/stencil isolation as ordinary blits.
The renderer probe reopens the same client across twenty contexts. It exposed
particle buffers surviving context destruction; their cleanup and context-local
state-cache reset now pass this exercise without GL errors. Eight of nine
original Debug instrument cases passed the next diagnostic run, including
repeat-identical real DG/DG-S cockpit captures. The remaining alignment/sync
fixture now selects the actual ISS target through stock scenario syntax, so
it exercises numerical instrument output instead of the empty-target prompt.

The original Debug/Release cross-check also found a pre-existing DG defect:
`FuelMFD::Tsample` was read without initialization. Debug's allocator fill and
Release's initial memory contents caused different first fuel-flow redraws at
simulation time zero. Run 41455123551 preserves those failed original captures
(Debug ZIP SHA-256 `b5146b99c785891b8ecdeb795ad60df7d5836d73009106df0851080038ef477c`,
Release `3a14150617253cf0a5f592c96f90f2381a0aaf338b2c6563f24848b9cde8a15e`).
These captures cannot qualify as a reference. A single constructor assignment
now initializes that timer from the current simulation time. No fuel-flow
formula, physics code or comparison budget changes. The source checker retains
all original pins and separately verifies the exact one-line repair. A complete
Windows application/SDK rebuild and new cockpit captures are required before
extraction; the original pre-repair runtime must not be mixed with this source.

Before extraction, require repeat-identical numerical and displayed-text traces,
finite finalized state, actual expected cockpit/MFD modes, numerical display
calls, normal real window/context teardown, no GL errors and SSIM at least 0.98.
The original orbital/propulsion budgets remain unchanged. Failed probes are
diagnostics, never accepted references. Capturing a golden requires successful
Debug/Release repeats and cross-configuration comparison; accepted references
will not be refreshed automatically.

After this gate, extract original instrumentation and panel/VC services behind
explicit platform boundaries. Keep Windows adapters, preserve calculations and
callback order, and add native surface/blit/font/mesh/input support through the
shared renderer. Then source-build DG/DG-S, compare original displayed precision,
validate picking and controls on the actual vessel, and run the required stock
scenarios. A prototype overlay cannot satisfy these gates.

Extraction starts with a private cockpit graphics binding. On Windows it is a
type alias for the original `GraphicsClient`, retaining exact pointer types and
function signatures. Native builds bind to the real `NativeGraphics` contract.
The first Pane/HUD/MFD/panel declaration changes preserve all calculation and
callback tokens, checked against the pinned Windows source by
`Tests/Production/cockpit_source.py`; the native header also compiles without
Windows or graphics-library headers. This preparatory boundary does not yet
build or run the native instrumentation classes.
Configuration access now uses the existing camera/session service's live Config
object, including writes to HUD settings. The same graphics binding covers
default panels, Panel2D, VC and vector-map marker lists. Source conservation
checks verify these substitutions before the earlier map-flags audit inspects
its preserved predecessor. No instrument formula or scheduler changes.
The first boundary passes the current Windows application/SDK and all nine
frozen cockpit regressions in
[run 41464854668](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41464854668),
including the Debug/Release comparison. All four native Debug/Release and
automatic/SSE2 configurations pass in
[run 41464853680](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41464853680).

The next extraction shares cockpit SDK records, callback scalar types, HUD/MFD
mode constants and packed button-menu records. Windows aliases retain original
field types and callback signatures. Complete source reconstruction checks and
native/Windows layout tests cover this boundary; native instrument classes are
still not operational.
The original ImGui dialog declaration and help-context record are shared too,
preserving Windows class methods and virtual ordering. Instrument/selection
headers now use platform SDK scalar/drawing types and isolate Windows-only
Direct3D/GDI declarations. A separate native declaration test compiles the
original abstract `Instrument` and selection inheritance without Windows
headers. Runtime methods, MFD drawing, panels, controls and DG remain separate
unfinished integration work.

Dedicated development workflows cancel older runs in the same branch group.
A bounded maintenance workflow prunes only older active production checks;
completed evidence, reference capture/preservation workflows and newer runs
are excluded. Inherited application, Nightly and Artifact Cleanup workflows are
unchanged.

All ten stock instrument declarations now compile natively, including their
original vector-map data. Orbit/transfer plotting uses the extracted original
`MfdOrbitGeometry.cpp` in the shared production boundary on both platforms.
Source reconstruction proves the implementation, constants and screen-mapping
code were moved unchanged. Independent tests exercise forty conic projections
(circular, eccentric, inclined and hyperbolic), analytical pixel bounds, marker
coordinates, clipping and invalid hyperbolic scales. This is actual instrument
geometry code; the native instrument scheduler, drawing and cockpit runtime
remain unfinished. Windows cockpit image/numerical regression is still required
for this extraction.

The SDK/declaration extraction at `a716a8e3` passes the complete current Windows
application/SDK and all nine frozen cockpit comparisons in
[run 41471188840](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41471188840),
including the Debug/Release comparison. The four native configurations pass in
[run 41471188877](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41471188877).

The next stage compiles the actual implementations of all ten stock MFD modes
as native objects, with original Windows algorithms and callback ordering
verified by reconstruction. It shares original panel mouse-event constants and
uses explicit drawing, color, configuration-path and case-comparison services.
The align-plane saved defaults now use a boolean zero in the boolean slot
and floating-point zeros in the two angle slots; this preserves all initial
values and fixes a narrowing initializer rejected by GCC.

Native brush, device-color fill, whole/rectangular blits, overlapping self-blits
and default SDK `oapiBlt` delegate to the existing shared OpenGL implementation.
The renderer probe verifies real pixels and resource teardown across twenty
contexts, including drawing into a compressed stock texture. Obsolete SDK
color-key arguments fail explicitly on native builds. This stage does not yet
link the native instrument lifecycle or make DG/DG-S cockpits operational.
The original application call forms and Windows SDK class/field layouts remain
unchanged. Current Windows image/state comparisons are required before this
stage is accepted.

The original `Instrument` base/factory/scheduler also compiles as a native
object, alongside the ten stock modes. Instrument orbital-element calls now
pass the original session reference epoch and simulation time explicitly.
Windows adapters return the same original globals; native bindings query the
authoritative production services. Selection, input, help and pane access must
be bound by the future native cockpit owner and fail explicitly if absent.
Deprecated GDI rendering, the legacy map and custom MFD factories remain
explicitly unavailable on native builds at this stage. Windows keeps their
original implementations. This compilation gate does not exercise a runnable
native instrument scheduler or satisfy the Phase 6 cockpit gate.
The modern vector-map implementation also compiles natively. Its Elements
records receive the same explicit epoch. Native coast/contour files use the
indexed configuration resolver, marker text remains UTF-8 through the real
Sketchpad, and display-based font sizing queries GLFW's actual primary display
mode. The Map MFD subsequently overrides that initial label size using
`max(9, IH / 40)`, so its labels follow instrument height. Desktop/viewport
metrics are recorded for other vector-map users and reproducibility.

The stock-mode implementation/drawing-adapter stage at `1b146567` passes
current Windows application/SDK tests and all original cockpit image, numerical,
geometry and displayed-text comparisons in
[run 41474774584](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41474774584),
including Debug/Release cross-comparison. All four native profiles pass their
full existing flight/lifetime/terrain checks and the native instrument
compilation/pixel probe in
[run 41474774464](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41474774464).
The subsequent scheduler/map/session-binding stage has local source, compilation,
conic and twenty-context pixel verification, plus unchanged native exterior
state and SSIM `0.9881491503795506` in two fresh processes. These local results
are separate from the required hosted validation of that later stage.

Before extracting cockpit mouse routing, `Tests/Production/CockpitControls`
adds an original Windows control gate using exact archived pre-extraction
application/SDK/client binaries. The additional driver sends recorded mouse
messages through the actual owned render window, including real DG/DG-S VC
hit testing, then verifies the actual vessel's RCS mode. Five cases each run
twice per Windows configuration. These outputs remain diagnostic until every
repeat and Debug/Release comparison passes the unchanged budgets. The existing
nine-case references remain immutable; native cockpit input work must wait for
this additional gate.

The scheduler/map/session-binding stage at `881a06d0` passes the complete
Windows application/SDK and nine frozen cockpit regressions, including
Debug/Release, in
[run 41480059260](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41480059260).
All four native profiles pass in
[run 41480059302](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41480059302).
The additional original control gate passes all five cases, two processes per
configuration, and cross-configuration comparison in
[run 41482729373](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41482729373).
Independent local archive/hash and comparison checks confirm zero numerical
differences, exact input/text/geometry/lifecycle repeats and image SSIM 1.0.
The accepted control provenance is frozen separately under
`CockpitControls/Reference`; capture is now manual-only. This establishes the
control reference prerequisite without claiming native input integration.


The original mouse-control archives are preserved in
[versioned release storage](https://github.com/dcajacob/orbiter-cross-platform/releases/tag/production-windows-cockpit-controls-v1).
[Preservation run 41487758735](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41487758735)
verifies a fresh public download against the accepted hashes and canonical files.

Native panel rendering now exposes the existing shared renderer's surface,
texture, reference-count and panel operations through the private cockpit
contract. The pixel probe reproduced a shared renderer defect: a requested
50% panel opacity produced fully opaque red. Both renderer adapters now apply
the requested alpha and additive blending, isolate depth/stencil state and
reset opacity for subsequent surface copies. Twenty context cycles verify
actual pixels at opacity 0, 0.5 and 1 in regular/additive modes, invalid-alpha
rejection, surface reference lifetime and subsequent scaled copies. This is a
graphics primitive test; it does not stand in for stock cockpit integration.
The original Windows SDK and graphics-client signatures are unchanged.
