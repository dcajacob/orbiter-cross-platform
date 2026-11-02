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
