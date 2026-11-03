# Phase 6 cockpit and instrument integration

Phase 6 is in progress. The accepted Phase 5 laptop preview runs the production
ShuttlePB/ISS external view. In the separate Phase 6 candidate, both stock
Delta-gliders fly with the original Lua autopilot in the 2D panel and virtual
cockpit. Local instrument rendering and real RCS-switch clicks pass the frozen
Windows comparisons for both gliders. All nine frozen instrument cases and five
RCS-click cases passed locally in Debug. The stock flight recorder now drives
the native vessel and cockpit camera through five unchanged DG scenarios.
The tutorial text is drawn and both automatic and pilot-commanded returns
to free flight pass locally.

The native graphics leak now has an isolated source fix and a passing local
sanitizer menu flow. Mesa's executable-code allocator retained two bookkeeping
objects (112 bytes) and a 10 MiB mapping after its last generated function was
freed. A checksum-pinned Mesa 26.0.8 candidate releases both under the existing
allocator mutex. The unpatched source reproduces the leak; the patched source
passes standalone EGL teardown, overlapping live-code ownership, failed
allocation cleanup and 4,000 concurrent allocations. The complete ASan
menu/Help flow and fresh Options reload pass with the candidate explicitly
selected, without suppressions. This is an isolated software-driver result;
the system driver is unchanged and broader platform qualification remains open.
[Reproduction, patch and build instructions](../../Tests/Production/GraphicsDriverLifetime/README.md)
Earlier system-driver failures below are retained as historical evidence.

With that candidate selected, unsuppressed ASan/UBSan/LSan now also pass the
five-process recorder/player/editor sequence (260 presentations) and twenty
in-process GUI sessions with an input dialog open (80 presentations). Four
DG/DG-S Lua AAP flights in the 2D panel and virtual cockpit plus six unchanged
stock scenarios pass all 552 presentations and teardown. The broader stock
run exposed an additional Lua camera ownership error in Earth views: a
64-byte track-mode object was deleted through its 24-byte nonvirtual base.
The command now uses the same concrete-type deleter as the engine's camera
preset and recorder paths. Its calculations and the SDK class layout are
conserved. [Local lifetime evidence](GraphicsLifetimeVerification.json)

The expanded sanitizer census completes all 38 currently loadable unchanged DG
scenarios, with 2,280 presentations and clean context teardown. Geostationary
orbit exposed a HUD heading-marker use-after-scope: branch-local vertex arrays
expired before the mesh write. The write now runs inside its branch, preserving
every original coordinate, texture value and index expression. The original
method fails the new CPU regression; the fixed method passes 24 marker cases
and the real stock scenario. GeneralApiTest's existing planet-status Lua
assertion remains reported as a failure. The census now recognizes the
sanitizer build's `LuaCall` error prefix and retains sanitizer failures even
when no lifecycle file was written. This is smoke coverage, with broader
interactive stock acceptance still required.
[HUD and stock-census evidence](HudHeadingVerification.json)

The preserved Windows 2025 Lua/AAP candidate now passes both default-profile
and SSE2 Debug/Release comparisons for all five cases: zero physical-state
error, exact Lua/control traces and frame/MFD SSIM 1.0. Native Debug and Release
automatic-profile runs also match all five candidates' event, control,
atmosphere and cockpit-state traces exactly after aligning latitude dispatch
with that CRT family. Windows 2022's legacy default comparison still fails.
Durable Lua reference preservation, complete SSE2 native simulator parity and
the broader Phase 6 platform gates remain open.
[Native numerical evidence](LuaNativeAlignment.json)

The cockpit now draws the original target, time and frame-rate displays and
opens the original spacecraft selection dialog on F3. A two-vessel run used
the dialog to select DG-S and then return to DG. Both the control focus and the
internal camera followed each selection. With info bars visible, the target
name, camera mode, field of view, MJD and simulation time appeared in the upper
corners. The auto-hide capture matched the visible frame with the pointer over
the bars and the hidden frame after it moved away. Native rendering checks,
a preserved-Windows diagnostic and optional exact state/image comparison live
in `Tests/Production/CockpitUI/focus_bars.py`. Windows comparison of this
addition passed with the automatic CPU profile in both configurations. The
forced-SSE2 capture first differed from the automatic Windows trace in the
orientation matrix at tick 38. The paired workflow now also captures Windows
with SSE2 selected. [Hosted spacecraft comparisons](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41563089040)

The native cockpit now draws the original dynamic menu and stock PNG icons.
Ship, Camera, Speed, Pause, Function, Info, Options, Map, Record, Help, Save and Exit are connected. In a local
X11 flight, mouse clicks paused and resumed the DG, changed the clock to 10×,
switched focus to DG-S, and opened the original camera, object information,
map and menu configuration dialogs. The saved scenario contains the selected
DG-S and camera. F4 switched the menu between visible and auto-hide modes.
Dragging Ship past Camera persisted their new order. Exit closed the graphics
context after all 162 frame presentations. The sanitizer run completed 125
frame presentations, with two 56-byte allocations originating in Mesa
libgallium 26.0.8 at offsets `0xef1ba0` and `0xef1b89`.
Help now opens the original documentation in the desktop browser; details and
the separate remaining Phase 6 gates are below.
[Delta-glider flight evidence](DeltaGlider.md)

The Help command, Alt-F1 and the original dialog question-mark buttons resolve
the original `HELPCONTEXT` book/topic through a staged catalog. The desktop
browser displays local HTML with contents, keyword index, full-text search,
Back/Forward and the original page imagery. Vessel and Scenario buttons use
the current focus vessel's `Help` configuration and the scenario's `Help`
metadata. Unknown books or topics produce a notification. A missing optional
add-on context does not prevent the requested stock topic from opening.

The development provisioner builds 21 original help books, including stock
scenario tutorials, DG/DG-S, AAP, scenario-editor documentation and the Lua API.
It runs the repository's LDoc/Penlight/LuaFileSystem sources against the original
Lua API annotations. Generated Lua docs include the DG and ShuttleA extensions.
The manifest hashes generator inputs, the Lua/LuaFileSystem binaries and all
401 original/copied inputs. Browser copies adapt case-sensitive paths,
Windows CHM jumps and encoding; the source bytes are retained separately.
The audit checks unchanged prose across 189 topics and resolves all 2,170
local links. It also accounts explicitly for two malformed original anchor
tags and legacy missing-path links; it does not rewrite help prose.

To prepare Help after building the cockpit engine:

```sh
python3 -B Tests/Production/Help/prepare.py \
  --lua out/phase6-cockpit-engine/native-lua/lua \
  --destination out/phase6-dg-resources/Help
python3 -B Tests/Production/Help/verify.py \
  --help-root out/phase6-dg-resources/Help \
  --output out/help-sources.json
```

Local Chromium checks render each book's default topic and images, exercise
contents/index/search, history, cross-book navigation, generated Lua docs and
vessel/scenario buttons. The actual X11 Debug menu flow passed 670 presentations
and teardown: Help, Alt-F1 and the camera question-mark button each reached
`xdg-open`, then an isolated real browser rendered `mainmenu.htm`,
`mainmenu.htm` and `cam_mode.htm`. Each request carried current DG-S and
Quickstart scenario context. All twelve commands, recorder overwrite handling,
Function callback ownership, Options persistence/reload, reorder, Save and Exit
passed in that flow. The hosted matrix now runs these checks with a pinned
Playwright browser driver and retains the source manifest and screenshots.
The equivalent Release flow passed 743 presentations, all three help launches,
the same context checks and complete graphics shutdown.

The desktop launcher receives a single encoded URL, without a command shell.
It does not inherit simulation file descriptors or engine loader/preload paths.
The help service polls child exits across simulation sessions, reports desktop
launcher failures and never terminates the user's browser. A separate process
test checks exact arguments, descriptor/environment isolation, missing launchers,
nonzero exits and child reaping. It passes address, undefined-behavior and leak
checking without suppressions outside the ptrace-based execution sandbox
(LeakSanitizer cannot operate under that sandbox). These Help checks do not close the existing
Mesa leak gate, default Windows numerical mismatch, broader stock-vessel
coverage or physical-controller qualification requirements.

The recorder commit's Windows build was initially stopped by a CRLF-sensitive
source-audit replacement. `62472a6f` normalizes line endings and limits the
destructor cleanup adaptation to the destructor itself. LF and CRLF checks
both pass and both reject removal of the original Load() filename cleanup.
The complete 439-file source-conservation audit and frozen UI/control/MFD
reference checks pass unchanged locally.

The original notification implementation is now shared through
`GuiNotifications.inc`. Native Help failures and scenario-save messages use
the same widgets, colors, timing, duplicate counter and dismiss/copy controls
as Windows. Native session teardown clears queued notifications before
destroying ImGui. The final Debug and Release menu flows completed 703 and
821 presentations respectively, including a public-SDK missing-book request
repeated twice and displayed as one `Orbiter Help (x2)` error. The notification
code is compared against the original source after the export macro adapter.
The instrumented menu flow completed 700 presentations and additionally
clicked the error's dismiss button and verified that it expired. Help browser
launches, contextual topics, and notification deduplication/dismissal passed.
No address or undefined-behavior errors were reported. Process exit still
failed with the same unsuppressed 112 bytes in two graphics allocations;
the subsequent Options reload was therefore not run in that sanitizer flow.

The Windows Debug and Release client regressions and their final comparison
passed at `607de492` in
[run 41574333629](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41574333629).
The additional preserved-Windows menu capture exposed a fixture mismatch:
the auto-hide check compared an eight-item menu with the original twelve-item
hidden menu. The Debug capture differed at 18 pixels on the topmost row;
the menu had retracted, but the original renderer's remaining edge pixels
depended on the configured menu width. A separate `menu-hidden` case now uses
the same eight items as `menu` and `menu-auto`. The twelve-item Windows case
remains intact, and the exact strip comparison excludes no pixels. All seven
cases pass locally in native Debug, including selection, reveal, retraction
and complete graphics shutdown. The corrected preserved-Windows fixtures pass
in Debug and Release with both math profiles in
[run 41578889992](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41578889992).
The paired native comparison remains a separate gate.

The original Options dialog now uses the live native world, configuration and
cockpit. All ten pages open in the actual X11 mouse test. Debug and Release
both changed the MFD refresh interval from 0.25 to 0.35 seconds, scaled the DG-S
panel to 1.1, disabled fuel consumption, switched through the virtual and glass
cockpits, and increased the glass MFD render target from 346 to 377 pixels.
F6 opens Options and Ctrl-F9 opens its visual-helper page. F8, view/panel
switching, camera lean/reset, HUD color and planetarium/label shortcuts route
the original logical key bindings to the real cockpit and camera methods.
The Windows Options pages and helper widgets retain their original bodies;
`cockpit_source.py` checks the explicit service substitutions and shared widgets.
An additional sixty-frame Options schedule clicks the same original controls
on both hosts and captures full frames at ticks 20 and 50. Its native execution
passes locally; the paired Windows state/image check is pending hosted CI.

After Options has been opened, normal native session shutdown atomically saves
the live settings to the explicit `--config` file, using the original Config
writer plus native raw-axis assignments. Subsequent Debug and Release launches
restored the selected settings and actual 377-pixel render target. The test
archives the final config and read-only per-frame option/render-target records.
The accepted Phase 5 external-view executable keeps its existing controls.
The instrumented nine-command flow completed 336 frame presentations and
destroyed its graphics context without address or undefined-behavior errors.
LeakSanitizer still failed on the same two 56-byte Gallium allocations at
`0xef1ba0` and `0xef1b89`; no suppressions were applied.

The native joystick page enumerates real GLFW devices and their available raw
axes. Device zero disables joystick input. Configured deadzone and throttle
saturation now affect the sampled controls; throttle acquisition retains the
original eight-count bins and movement threshold. Since GLFW does not expose
DirectInput axis identities, native axis choices are numbered from one in the
UI and stored as zero-based indices in `NativeJoystickThrottleAxis` and
`NativeJoystickRudderAxis`. Explicit CLI assignments take precedence. A throttle
value of -2 uses the existing config's conventional Z/slider positions (raw
indices 2, 6 and 7); -1 selects keyboard-only throttle. The focused calibration
test covers deadzone endpoints, saturation, acquisition, noise, disconnect,
reconnection and reassignment. Physical controller acceptance remains pending.
[DirectInput calibration semantics](https://learn.microsoft.com/en-us/previous-versions/windows/desktop/ee417908(v=vs.85))

The Record menu and Ctrl-F5 now open the original recorder/player. REC starts
all live vessels' original position, attitude and articulation writers; Stop,
Ctrl-C and normal exit flush their final samples. Files are placed under
`Flights/<name>` beside the explicit `--save` destination, with a starting
scenario under `Playback/<name>.scn`. Names are normalized consistently with
native resource lookup. Existing recordings require the original overwrite
confirmation. Recorder options use the live configuration and persist when
the session closes. Time acceleration and focus events feed the original
system-event playback loop. The shared Windows focus adapter now also records
focus events when that existing option is enabled. The shared playback loop
honors the recorded-camera checkbox.

The original playback editor uses the real stream and camera. Commit writes a
temporary event file, replaces the destination and rescans playback. Editing a
flight from another directory creates a complete copy next to the user save,
including its original starting scenario; the source recording is retained.
Deleted events, the editor filename and factory-created camera modes now have
matching destruction. Restarting the shared vessel recorder clears its prior
sample storage before resetting it. The recorder sanitizer fixture also exposed
an uninitialized MFD flag when both displays were off. Pane now initializes
its MFD specifications, and legacy registration explicitly selects opaque off
screens; allocator contents no longer decide whether a blank texture exists.
The three-vessel recording also exercises an actual collision. Its hull-cache
animation copies were destroyed through the nonvirtual SDK base; they now
use their allocating transform type, preserving the SDK ABI and calculations.

`CockpitUI/recording.py` starts recording with original GUI controls, changes
thrust, focus and speed, stops with Ctrl-C, and loads the generated flight in a
fresh process. It verifies all three vessels (DG, DG-S and ISS), recorded focus
and speed, automatic playback completion, editor insertion/deletion/commit/
discard, and final samples when exiting while recording. The actual X11 menu
test also exercises both cancellation and confirmation of an overwrite.
The complete eleven-command flow presented 704 frames in Debug and 633 in
Release, then destroyed the graphics context. Both also restored Options and
the real MFD texture dimensions in a subsequent launch.
Local Debug and Release runs pass these recording and editor checks. A
60-frame recorder schedule is also included in the preserved-Windows/native
focus-bar suite: Ctrl-F5, REC, STOP and close, with frames at ticks 20 and 50.
The sanitizer sequence completed all 260 requested frames across five fresh
processes: recording, playback, editor, edited-flight reload and exit while
recording. No address or undefined-behavior errors remained. Every process
still returned LeakSanitizer's failure for the existing two 56-byte graphics
allocations; the logs and nonzero exits are retained without suppressions.
The physical sanitizer menu test also completed 562 presentations, two
recording starts and callback teardown. Its only leak frames resolve through
the captured live module map to `libgallium-26.0.8-1ubuntu0.3.so` offsets
`0xef1ba0` and `0xef1b89`; its nonzero exit remains a failed leak gate.
These are functional recording checks; paired Windows recording comparisons
and the full Phase 6 numerical gates remain separate requirements.

The Function menu and Ctrl-F4 now open the original custom-function dialog.
Native modules register and unregister real callbacks through
`oapiRegisterCustomCmd` and `oapiUnregisterCustomCmd`. The session owns each
command's label and description. Drawing uses a stable snapshot and rechecks
registration before dispatch, so callbacks can remove themselves or other
entries. Unique widget IDs distinguish identical labels. Windows uses the same
safe drawing path with its existing registry; the registry adapters are static
`DlgFunction` members so Windows retains its existing friend access. Unregistering
a Windows command now also releases its allocated label. Original button and tooltip rendering
is checked after these explicit lifetime adapters.

An SDK-only test module registers two identically named functions. Actual X11
clicks invoke both with their supplied contexts. The first unregisters itself,
forces registry reallocation with 64 temporary registrations, removes those
entries and installs a replacement. The second removes that replacement and
itself, then installs a sentinel that is removed during module teardown.
Debug completed 465 frame presentations and Release 474, with the complete
10-command menu, Options persistence/reload and graphics shutdown passing.
The isolated registry test passes address, undefined-behavior and leak checking.
The instrumented graphical flow completed 421 presentations and teardown, with
only the same two Gallium leaks totaling 112 bytes. A separate basic SDK
callback schedule captures the original Windows and native Function dialogs;
its paired state/image comparison is an additional hosted gate.

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
owning sources are checked before compiling the SDK-only control driver. At that
reference stage, Pane, HUD, stock MFDs, panel and VC code were unchanged. Later
extractions below are checked against this preserved behavior.

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


The panel opacity/surface bridge at `c98fad78` passes the complete Windows
application/SDK and nine frozen cockpit comparisons in
[run 41488621194](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41488621194).
All four native Debug/Release and automatic/SSE2 profiles pass their existing
flight, lifetime, terrain, instrument compilation and pixel checks in
[run 41488621168](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41488621168).

The next candidate links the original Pane, HUD, default panel, Panel2D, VC,
instrument scheduler and all ten stock MFD modes into the production engine.
Windows and native builds include the same original vessel/HUD/panel callback
bodies, with exact Windows reconstruction checked by
`cockpit_runtime_source.py`. Original float projection stages are retained in
the private native camera adapter. The native owner creates the pane before the
world, initializes it after stock post-creation callbacks, updates it after
finalization/time/camera, renders its overlay inside the shared renderer, and
draws the original HUD before presentation. Focus and deletion reach the actual
pane. Legacy bitmap panels, external/custom MFD plugins, menus and compiled help
remain explicitly unsupported; visible menu/info bars are rejected in this
candidate.

Local GCC Debug validation of five glass-cockpit cases runs two fresh processes
per case, 60 quarter-second steps each. All 61 state rows match original Windows
exactly, as do displayed text, projected geometry and HUD atlas updates. Every
native numerical and pixel repeat is identical. Minimum full-frame SSIM is
`0.9998722026987531`; minimum actual MFD texture SSIM is `0.9989917277303125`.
The original budgets and frozen captures are unchanged. These local results
still require hosted validation of this extraction; they do not qualify DG,
2D/VC interaction, native selection dialogs or the complete Phase 6 gate.

Initial diagnostics exposed two adapter errors. The existing external host used
the physics quantum as system time, whereas Windows uses three 10 ms startup
steps and caps subsequent system steps at 100 ms. The native cockpit now uses
that original policy while production TimeData retains its fixed physics step
and time acceleration. State and complete drawing traces then match Windows.
The original vector map treats absent contour files as optional. Its indexed
native path now preserves that file-open behavior; required world/module assets
still use strict resolution. No contour geometry is synthesized.

Build the separate candidate with `ORBITER_BUILD_NATIVE_COCKPIT=ON` and
`ORBITER_NATIVE_UI_ARCHIVE=/absolute/path/to/verified/imgui.zip` in addition to
the existing native vessel/celestial options. The ImGui archive hash comes from
the existing renderer lock. Build the matching separate native renderer against
that engine, then snapshot both with `Flight/prepare-preview.py`. Run:

```sh
python3 -B Tests/Production/Cockpit/frozen.py --cache out/cockpit-reference-cache --output out/frozen-cockpit
DISPLAY=:98 LIBGL_ALWAYS_SOFTWARE=1 GALLIUM_DRIVER=llvmpipe \
  python3 -B Tests/Production/Cockpit/native.py \
  --executable /absolute/candidate/bin/orbiter-production \
  --assets /absolute/stock-resources --data /absolute/celestial-data \
  --modules /absolute/candidate/NativeModules --planets /absolute/planet-data \
  --frozen out/frozen-cockpit --configuration Debug --output out/native-cockpit-evidence
```

Use an owned X11 display or `xvfb-run` at 1280x720 or larger. The capture viewport
is always 1280x720. The dedicated native matrix builds this candidate separately
from the accepted external/flight engine and archives its traces, images, logs
and build metadata. The ordinary laptop launchers continue to use Phase 5.


The first sanitizer cockpit run stopped at `Camera::Update`: `rot_smooth` had
never been initialized before an input-free internal camera update. The shared
constructor now initializes it to `false`, matching `Camera::Rotate`'s explicit
API default. Source conservation permits only that initialization, alongside
the prior accepted constructor repairs. Formulas, branch order, public SDK and
frozen references are unchanged. New hosted Windows comparisons remain required.


LeakSanitizer then attributed 660 bytes in 24 allocations to VectorMap's owned
font, pens and brushes. Its existing `CloseGDIResources` routine had no caller.
The shared destructor now calls that original release routine after releasing
the map surface. No instrument calculation or drawing changes. The before-fix
sanitizer log remains local evidence; repeat-session checks follow the repair.
Native selection/input/help services remain deliberately unbound until real UI
frame/input integration, so requests fail explicitly. Cockpit saves delegate to
the original Pane writer; redraw and focus/deletion events reach the actual pane.


After the repairs, actual Map/HSI cockpits create, render and destroy twenty
sessions without GL, memory-access or undefined-behavior errors. LSan reports
no remaining map-owned allocations. Unsuppressed X11/Gallium retention remains
46,253 bytes/791 allocations per context (925,060 bytes/15,820 for twenty distinct
contexts). This is an external retention limit, not a global leak-free claim;
it differs from the earlier Phase 5 object-cycle test, which reused one context.


The final cleanup candidate also verifies the production Windows mesh-before-
world destruction order across twenty real sessions. A separate native smoke
save/reload restores the actual Surface HUD and Map/HSI MFD modes through the
original writers/readers. This checks mode persistence; full Windows round-trip
and DG-specific persistence acceptance remain separate unfinished gates.
The unchanged default exterior host still reports SSIM `0.9881491503795506`
in two fresh processes with identical accepted state comparisons.

The original instrument-owner extraction at `809dbca7` passes both complete
MSVC application/SDK builds and all nine original cockpit cases in
[Windows run 41497790178](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41497790178).
All four Ubuntu 24.04 GCC Debug/Release automatic/SSE2 profiles pass their
existing flight, lifetime, ground and native instrument gates in
[native run 41497790041](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41497790041).
These runs establish the original ten MFDs and HUD on the native production
world. They do not establish native DG/DG-S or complete interactive cockpit UI.

## Native glass control routing candidate

The next candidate queues real GLFW left/right button and wheel events with
framebuffer coordinates, then invokes the original running Pane handler followed
by its system handler. A consumed button press prevents the external-camera drag
from also acting on the same press. The private renderer contract changes with
the native build fingerprint; the public Windows SDK remains unchanged.

`Tests/Production/CockpitControls/native.py` replays the immutable Windows glass
control schedule through those same native Pane handlers, without setting the
vessel's RCS mode directly. Two fresh 60-step processes verify ROT to LIN to ROT,
the exact eight tick/event/coordinate records, finalized state and drawing output.
Local state differences are zero; projected overlay differences are zero pixels,
display text and HUD atlas updates match exactly, direct MFD SSIM is 1.0, and
full-frame SSIM is at least `0.9999991241682158`. Windows CRLF versus Linux LF
is normalized only when reading the discrete input CSV; all reference file
hashes are verified before comparison and preserved unchanged.

`mouse_smoke.py` separately delivers targeted X11 events and moves the real server
cursor in its own process's window. It verifies the actual GLFW callback,
coordinate conversion, original ROT/LIN hit testing, momentary keyboard thrust,
focus-loss release, MFD power off/on and Surface/Orbit mode selection through the
original buttons, finalized zero jet/exhaust samples, presentation and shutdown.
The local run passes with 145 finalized release samples. This is distinct from
the deterministic replay test. Wayland/high-DPI mouse validation remains pending.

Both checks are added after the original instrument gate in every native CI
profile. `current.py` also adds all five original Windows glass/DG/DG-S 2D/VC
mouse cases to the current application/SDK regression, with unchanged budgets,
repeat checks and direct MFD readbacks. Hosted results for this new routing stage
must pass before acceptance. The frozen producer scripts, original DLLs and
accepted captures are not regenerated. These are engineering candidates;
ordinary laptop launchers remain at accepted Phase 5.

The new private input contract also passes the existing default-flight keyboard
and lifecycle suite locally: all 24 full/fine ROT/LIN hold/release combinations,
403 finalized zero-thrust samples, child focus/previous focus, aerodynamic
controls, pause/single step, quicksave and in-process reload. This uses a separate
snapshot of the default engine and matching renderer, without changing either
accepted laptop launcher.

The real RCS/MFD mouse test also passes with ASan and UBSan: no memory-access or
undefined-behavior errors during power cycling or instrument replacement. Full
unsuppressed LSan reporting remains enabled and reports the prior 46,253-byte,
791-allocation graphics retention. All 71 allocation-size/count report blocks
match the prior one-context baseline. `LSAN_OPTIONS=exitcode=0` lets the input
harness finish; the complete leak report is checked separately. This does not
establish globally leak-free rendering.

Hosted native run [41502859573](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41502859573)
passes all four Debug/Release automatic/SSE2 profiles at `23ab2367`, including
frozen instrument and RCS comparisons and the actual X11 RCS/MFD input test.
Windows run [41502349620](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41502349620)
passes both application/SDK builds, all nine cockpit comparisons and all five
control cases against the frozen originals. The final cross-configuration
instrument comparison also passes. Its control comparison stops during provenance
verification because the comparison job has a shallow checkout. Commit `53405176`
sets full history for that job and adds the missing `CockpitControls` push trigger.
The fix is verified by [run 41507189054](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41507189054)
at `881dd518`. Both Windows builds and all final cross-configuration comparisons
pass, completing the hosted glass mouse-control gate. Selection/input UI and
real native DG/DG-S cockpits remain unfinished.

### Original selection and input reference

[Run 41541262748](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41541262748)
passes original Windows Orbit target entry, Sync transit-list parameter entry
and SDK input cancellation in two fresh processes per Debug/Release build.
The preserved application/SDK/client binaries supply the actual dialogs and
MFD callbacks. The additional observer routes declared mouse/key/character
messages through its owned render window and records popup bounds, capture
flags, callbacks and saved instrument settings.

The three cross-build cases have zero numerical and projected-geometry errors,
exact instrument text, popup/input/callback records and SSIM 1.0 for all captured
full frames and MFD textures. Local artifact SHA256 verification and comparison
also pass. The producer, artifacts and per-file hashes are in
`Tests/Production/CockpitUI/Reference`. Native UI integration and additional
menu/focus coverage remain pending.

### Native selection and parameter input candidate

The engine owns one ImGui CPU context and the original Select/InputBox objects.
The separate renderer uses the pinned GLFW and OpenGL3 backends, with the
original styling and fonts. Keyboard capture follows the original dialog and
focus policy. Mouse capture precedes Pane routing, and release clears camera
capture even when a popup owns the mouse. Backend shutdown precedes context
shutdown. The icon font buffer is atlas-owned to repair the inherited 426,112
byte allocation leak from file loading with borrowed-buffer ownership.

Three local native cases pass against the preserved original Windows UI
captures. Inputs and popup state are exact, numerical and projected-overlay
errors are zero, all MFD readbacks have SSIM 1.0, and popup SSIM is at least
0.9955073. Full-frame SSIM is at least 0.9999420. Repeat frames and MFD pixels are
exact. The native replay uses the same 120 ms wall-clock delay as the original
capture driver so the original popup fade runs on comparable timing. Numerical
step size and image budgets retain their frozen values.

A separate actual X11 test passes target typing, Sync parameter entry,
cancellation, typing without flight thrust, and return to flight controls.
The existing RCS/MFD mouse regression passes with 150 finalized release samples.
The default-engine keyboard/lifecycle regression passes with 424 finalized
release samples. Twenty ASan/UBSan GUI sessions also shut down successfully with
an input dialog open. After the font ownership repair, LSan reports two remaining
allocations totaling 112 bytes per context, or 2,240 bytes across
20 contexts. Live process mappings place both allocation callers in the system
Gallium library at offsets `0xef1ba0` and `0xef1b89`. Hosted verification remains
pending.

The test resource helper stages the hash-verified original manuscript font from
the existing source tree for disposable tests. General asset staging continues
to exclude that publication-restricted font. Packaged font distribution remains
a release dependency. [Local UI evidence](CockpitUIVerification.json) records
this candidate. Full Phase 6 acceptance still requires broader menu/focus and
Delta-glider/DG-S cockpit and systems coverage.

The additional fixed-clock Windows UI captures are preserved in
[production-windows-cockpit-ui-timing-v1](https://github.com/dcajacob/orbiter-cross-platform/releases/tag/production-windows-cockpit-ui-timing-v1).
Run 41551358542 recorded sixty consecutive 0.25 s ImGui frames for each of two
repeats of all three cases in each configuration. The preservation job verified
the public release archives independently. The ordinary live UI still uses its
platform clock.

The bounded native replay now records the same effective frame deltas. The
local Debug replay compared both original sets and passed all six runs.
Selection, Sync list entry and cancellation had identical input schedules and
popup states. Popup crop SSIM was 0.99555, 0.99556 and 0.99551 respectively.
Full-frame SSIM against the timed originals was at least 0.99994, with zero
projected geometry error. The comparison includes the caret. Hosted native
Debug/Release and both math configurations are separate acceptance checks.

The native cockpit also runs the original `Instrument_User` and `MFD2`
Sketchpad path needed by Lua vessel modes. A local integration probe registered
a mode, received the extended-open notification and the packed-dimension
fallback, restored its default status, and consumed a public SDK button event
and buffered key. It drew its title and text 30 times through Sketchpad. The
captured 346 by 346 left display contained 1,518 colored pixels at frame 20.
The saved scenario contained the mode's custom status line. Shutdown called
store, close and destruction in order. The original Windows SDK declarations
and virtual method order are checked against f7251942. The native Lua vessel
bindings and full stock vessel runs are still separate gates.
