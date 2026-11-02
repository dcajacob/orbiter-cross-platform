# Phase 5 attachments and live vessel lifetime

The native production host now supports original vessel attachments, runtime
vessel creation, deferred deletion and focus changes. Phase 5 is accepted for
the reduced production ShuttlePB/ISS scope: local checks and all required hosted
Windows/Linux gates pass.

## Implementation and scope

`VesselLifetime.h` shares the original Windows `SetFocusObject`, `InsertVessel`
and `KillVessels` algorithms with the native host. Windows adapters retain pane,
dialog, console, plugin and graphics notifications. Deletion retains the original
reverse order, proxy/nearest surviving focus selection, previous-focus clearing,
camera retargeting, world notifications and final object destruction.
`lifetime_source.py` reconstructs the pre-extraction bodies at `88eaa185` and
checks their identity after explicit service substitutions. Windows SDK layouts,
exports and virtual ordering are unchanged.

The native SDK delegates `oapiCreateVessel`, `oapiCreateVesselEx`,
`oapiDeleteVessel` and focus/enumeration calls to the real world and vessel
constructors. Attachments use the existing vessel SDK and composite dynamics.
New stock visuals are registered immediately and refresh visibility after the
next camera update. Deleted visuals and pending registrations are released before
their engine objects. Native vessel interfaces are released before their shared
libraries close.

The accepted host remains restricted to real Sol, configuration-driven ISS and
source-built ShuttlePB classes. Saved graphs may contain multiple instances and
arbitrary supported vessel names, including a surviving child after the original
PB is deleted. Missing or incompatible modules fail explicitly. This does not
establish general stock scenario or add-on compatibility.

Native F3 cycles focus-enabled vessels; Ctrl-F3 selects the previous vessel.
Windows retains its existing F3 selection dialog. RCS still fires only while a
direction key is held. Creation, deletion and attachment exercises use the
recorded SDK control driver; a scenario editor UI belongs to Phase 7.

Application plugins, panels and dialogs remain outside this external-view host.
The native `module.create/delete/focus/pre/post` trace rows mark the original
host notification positions; they do not claim application plugins are loaded.
Actual source-built vessel callback entries/exits are observed independently at
the original `Vessel.cpp` hook locations.

## Verification

The unchanged pre-extraction Windows reference is
[run 41193020450](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41193020450),
using application `391919027ac3e4a4d42f145373c788fc859c32cd`.
Its archived inputs, traces, budgets and hashes remain unchanged.

Local Debug/automatic-math results:

- Both 80-tick attachment and lifetime cases match every frozen sampled state
  with zero measured numerical error, at rendering intervals 4 and 17.
- All 1,364 attachment and 1,136 lifetime callback/notification events match in
  order, frame, tick, elapsed seconds and epoch, within the existing MJD budget.
- The created child uses the actual version-2 ShuttlePB module, stock mesh with
  7 groups, 2 materials and 2 textures, and 16 thrusters. Draw evidence confirms
  its geometry renders; registration, interface release and library close are
  verified.
- Nine supplementary cases cover focused deletion, Earth as alternative camera
  target, deletion of the original PB, simultaneous reverse-order deletion,
  twenty live create/focus/delete cycles using both creation APIs, dynamic graph
  save/reload, and original no-focus shutdown. State/checkpoint results do not
  depend on rendering frequency. Deleting either member of an attached pair
  also clears the surviving vessel's attachment relationship.
- Real keyboard input switches to Child, fires/releases its RCS, restores PB,
  and completes the existing flight, pause, single-step and in-process reload
  checks. Keyboard tests run on a dedicated display to prevent focus interference.
- The eight-case orbital suite and twenty complete session replacements pass.
  Ground/contact, controlled landing and unchanged scene checks also pass locally;
  scene SSIM is 0.9881491503795506 with zero landmark error.

AddressSanitizer/UndefinedBehaviorSanitizer instrumentation covers the native
engine, host and vessel modules. All supplementary lifecycle cases pass with
address/undefined checks enabled. The renderer is a separate uninstrumented
module. Leak diagnostics also exposed renderer-owned horizon/exhaust/spot GPU
resources and empty arrays; these now release while the graphics context exists.
Camera construction initializes its view mode and reference rotation before
setters read them. Remaining process-level X11/Mesa leak reports are recorded
separately and are not described as a clean global leak-sanitizer result.
The no-dynamic-vessel run and twenty-create/delete run have identical totals:
46,141 bytes in 789 X11 allocations and 112 bytes in two Gallium allocations.
No renderer-owned allocations remain in these reports; no suppressions were used.

## Hosted acceptance

[Native run 41396231078](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41396231078)
passes all four Ubuntu 24.04 Debug/Release and automatic/SSE2 configurations at
`d14fa794`. Each passes the eight frozen orbital cases, all nine lifecycle cases,
twenty session replacements, actual keyboard focus/control/reload, controlled
upright landing, seven ground cases and original scene/image checks. Every
attachment/lifetime numerical difference is zero. All 1,364/1,136 selected events
match the original order and timing at both rendering intervals.

The current [Windows application/SDK/client run](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41396081168)
passes both MSVC configurations and frozen scene comparisons, with SSIM 1.0 and
zero numerical/landmark differences. It uses implementation source `58a356af`;
`d14fa794` adds only two attachment/deletion tests and documentation. The command
`git diff --exit-code 58a356af d14fa794 -- Src Orbitersdk Extern OVP` proves the
production sources are identical.

The full [production-reference workflow](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41396231165)
passes current Windows builds/tests, original orbit/propulsion, all fourteen
repeated behavior cases, and Debug/Release numerical/lifecycle comparison.
[Portable tests/parity](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41396231140),
[terrain/world parity](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41396081173)
and [SPICE parity](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41396081209)
also pass. The inherited disabled Nightly and Artifact Cleanup workflows remain
unchanged.

[The evidence record](VesselLifetimeVerification.json) preserves run/source
identities, artifact links/digests, downloaded ZIP verification, numerical
profiles, measured results and local binary hashes. Full traces, reports, images,
build logs, module/asset identities and licenses remain in the archived artifacts;
downloaded copies are under `out/phase5-verification`. These records are observed
results, not new frozen references. Laptop Intel/Mesa XWayland checks pass all
nine lifecycle cases and repeat the scene at SSIM 0.9862598209696377 with zero
landmark error. The prepared orbital and ground launchers use the matching
immutable build snapshot.

Phase 6 is next: original cockpit, HUD/MFD, panel/VC interaction and real
Delta-glider/DG-S integration. The stock-playable release remains incomplete.

## Reproduce

Build the matching native engine, modules and separate renderer as described in
[NativeExternalView.md](NativeExternalView.md). Then run under Xvfb or an isolated
X11 display, supplying absolute verified asset, kernel/module and planet roots:

```sh
python3 -B Tests/Production/Flight/verify.py \
  --executable "$BUILD/orbiter-production" --modules "$BUILD/NativeModules" \
  --assets "$ASSETS" --data "$DATA" --planets "$PLANETS" \
  --configuration Debug --output out/lifetime-flight
python3 -B Tests/Production/Flight/lifetime_edges.py \
  --executable "$BUILD/orbiter-production" --modules "$BUILD/NativeModules" \
  --assets "$ASSETS" --data "$DATA" --planets "$PLANETS" \
  --output out/lifetime-edges
python3 -B Tests/Production/Flight/keyboard_smoke.py --lifecycle \
  --executable "$BUILD/orbiter-production" --modules "$BUILD/NativeModules" \
  --assets "$ASSETS" --data "$DATA" --planets "$PLANETS" \
  --output out/lifetime-keyboard
```

The dedicated native workflow runs these with Ubuntu 24.04 Debug/Release and
automatic/SSE2 math, alongside frozen scene, flight, ground and landing gates.
The existing Windows application/SDK/client/reference, portable, terrain and
SPICE workflows remain required. Full stock release, controller hardware and
performance acceptance remain later gates.
