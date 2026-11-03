# Native Delta-glider integration

Phase 6 requires the original Delta-glider and DG-S source modules, systems,
meshes, 2D and virtual cockpits, and Lua-backed AAP. Native vessel execution
and cockpit acceptance are still in progress.

## Current flight evidence

Both native vessels now load the stock Lua interpreter and LuaInline worker and
fly with the original AAP in the 2D panel and virtual cockpit. In each 48-frame
atmospheric flight the autopilot drives elevator, aileron and main thrust,
responds to speed retargeting, and operates the gear and nose cone. The native
runner also loads unchanged 60-frame stock scenarios including Venus descent,
Earth views, The Alps in 3D and DG ISS Approach. The entry-and-landing challenge
uses the original mixed-case vessel class. Galileo's first Ganymede flyby names
a missing focus target and relies on Orbiter's fallback to the first vessel.
Earth views engages its scripted time acceleration. The runner checks focus, frame presentation,
shutdown and Lua errors.

Across five Lua schedules, native Debug and Release each reproduce their
corresponding original Windows build at all 61 samples, including events,
controls, air data and cockpit state. The original Windows builds disagree with
each other. At tick 34 of the atmospheric DG flight, both passed the same
planet-local coordinate ratio (`0x1.e92199644661ep-2`) to arcsine. Debug
returned `0x1.fdf30f8d54923p-2` and Release returned `0x1.fdf30f8d54924p-2`.
The one-bit latitude difference carried into horizon airspeed, then into the
elevator at tick 35. The native Release engine now uses the pinned SSE2
arcsine for this equatorial conversion. The Jacchia-71 atmosphere uses the
pinned exponential for air density. The exact original cross-build gate
remains open. The separate SSE2 diagnostic passed all five schedules across
original Debug and Release. [Paired CRT diagnostic](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41563089062)
[Original Windows comparison](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41560881876)

The separate [CRT dispatch diagnostic](../../Tests/Production/CrtDiagnostic/README.md)
records actual loaded DLL versions and hashes on Windows Server 2022 and 2025,
including installed SDK providers, with 8,517 arcsine inputs and repeated fresh
processes. Its results diagnose runtime provisioning; they do not replace the
original simulator cross-build gate or change the native math profile.

The native client flies all five original DG recorded scenarios from the stock
position, attitude, control and system-event files. DG stunts draws the recorded
tutorial notes and switches cameras. Both Mojave scenarios also switch cameras.
Glider in orbit 1 returns to free flight at tick 341, following the last recorded
position at 85.00463713 seconds. In Glider in orbit 2 the pilot takes control
with Ctrl+C at tick 91. The regression verifies the source files against the
preserved Windows revision and records vessel, camera and control state. Hosted
Windows comparisons also check the rendered frames. Both automatic-profile
captures isolated an initial camera-direction mismatch in the two orbital
recordings. The native cockpit now leaves the first camera update to the
original simulation step. All five local Debug flights pass the comparison
against original Windows Debug. The position, velocity, vessel rotation,
angular velocity and MJD errors were zero at every sample. The initial camera
directions passed in both orbital cases. The ten full frames had SSIM values
from 0.99725 to 0.999999.
[Recorded flight checks](../../Tests/Production/CockpitUI/recorded_flights.py)

The local frozen instrument and RCS-switch comparisons passed for both gliders
in both cockpit modes. An F3 dialog run switched from DG to DG-S and back
through the original Select and Previous controls. The stock time and target
bars render in visible and auto-hide modes. The native menu supports all twelve
stock commands, including Record with its original playback editor and Help
with the original documentation, dialog topics and vessel/scenario context.
Local browser checks cover all 21 help books. Full platform, stock-scenario and
numerical qualification remain open; twelve connected commands alone do not
complete Phase 6.
Of the 122 stock scenarios containing a DG or DG-S, 38 use only vessel classes
this client can load. All 38 presented 60 frames and shut down. Thirty-seven
completed without script errors. GeneralApiTest reached its Earth obliquity
assertion, where the script expects a different value from the staged SPICE
Earth configuration. Both original Windows configurations also failed the stock
planet-status test, with Earth obliquity measured at 23.439801090036248°.
The other 84 scenarios require additional vessel classes.
[Stock scenario census](../../Tests/Production/DeltaGlider/stock_scenarios.py)
Sanitizer flights now finish without the previous aircraft initialization,
light destruction, panel texture and virtual-cockpit vertex-buffer errors.
LeakSanitizer still reports two 56-byte allocations per flight. Loader maps
place both allocation sites in Mesa libgallium 26.0.8.
Matching driver debug symbols now identify `u_mmInit`, reached from
`rtasm_exec_malloc` during mipmap generation. A
[standalone EGL reproduction](../../Tests/Production/GraphicsDriverLifetime/README.md)
reproduces the same 112 bytes without Orbiter, X11 or GLFW; its no-mipmap control
is clean. The driver retains its global executable-memory heap across context
destruction and never releases it on library unload. This identifies the cause;
the unsuppressed lifetime gate still requires a cleanup fix.

## Earlier integration milestones

The native `meshc` target uses the shared production CPU mesh reader and the
original resource-name scan to generate `meshres.h`, `meshres_vc.h`,
`meshres_p0.h` and `meshres_p1.h`. Build `native_dg_mesh_resources` in the
cockpit engine build. `Tests/Production/DeltaGlider/mesh_resources.py` compares
every generated definition with the original Windows-generated Lua SDK tables
at f7251942. All 195 definitions match locally, including the exterior's 122
groups, the virtual cockpit's 133 groups and the two panels' 12 and 3 groups.
The checked headers describe stock assets; runtime visual creation, edits,
panel/VC interaction and rendering require separate gates.

`Src/Module/LuaScript/Native` builds the original Lua 5.1 shared dependency and
command-line executable using the same library sources as Windows. The archive
is pinned to upstream commit 69ea087dff1daba25a2000dfb8f1883c17545b7a and
SHA256 18fdf2dd3756c0941d227c0eae0cf1f972b350d0ca7fce0052db9920eb06280b.
The source header matches the existing dependency notice hash. The local Linux
build reports Lua 5.1. Orbiter's `LuaInterpreter`, `LuaInline`, stock resource
resolution, scheduling and SDK services still need native integration.

The optional `--delta-glider` profile of `Tests/Production/NativeScene/prepare.py`
stages the stock DG/DG-S configuration, meshes, both texture sets, scripts and
scenarios in their original installation paths. The production resolver opens
the original files on Linux, including the mixed-case texture names in the VC
mesh. The disposable manuscript font is staged separately for cockpit tests.

`Tests/Production/DeltaGlider/visual_mesh.py` runs the native application with
a test observer on its real ShuttlePB visual. It adds the stock 133-group DG VC,
retrieves the per-visual device mesh through the original shared
`VESSEL::GetDevMesh` callback, edits the horizon group's texture coordinates
and reads the vertex back. The CPU template retains its original coordinate.
The probe also selects panel material 14 and texture 17, rejects out-of-range
indices, deletes the mesh and reuses its slot. A local 60-frame run completed
all presents and destroyed the graphics context.

This test exposed a crash in `Vessel::GetMeshName` after deletion. The shared
vessel SDK now handles empty mesh slots on name, visibility, offset and copy
queries. Copying an empty slot no longer allocates a mesh. The observations
skip deleted slots and still require identified assets for populated entries.
This verifies stock VC mesh services on a live visual. Verification of the
complete stock DG and DG-S vessel modules and their panel callbacks is pending.

The native cockpit build now compiles the stock common subsystem and panel
classes, fuel display, artificial horizon, angle of attack, HSI, vertical
speed, angular rate display and DG switches into `native_dg_instruments`.
The visual regression links the entire library with undefined symbols rejected.
The HSI queries Orbiter's original navigation transmitter objects. Panel
elements use the production CPU mesh append operation and device-specific
mesh edits. The regression also advances the original `AnimState2` actuator,
writes its stock scenario line, reloads it and closes it at the original rate.
These component checks precede execution by the complete Delta-glider module.

The native Lua build compiles the original interpreter's execution methods
and the LuaInline worker. Its handoff gives the simulator initial ownership,
supports nested waits and transfers execution to one worker per interpreter.
The local concurrency test completed 10,000 round trips per run and passed
20 consecutive runs. The native worker joins at shutdown. The full interpreter
bindings, module loading, original script execution and SDK timing comparisons
are still pending.

The five-case Windows Lua capture at ece22d20 passed both repeats in each
configuration. The cross-build check remained open. In atmospheric DG flight
the largest Debug/Release elevator difference was 7.12e-16 and the largest
aileron difference was 2.43e-16. The other four cases had identical control
traces. [Paired Windows run 41553783639](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41553783639)
repeated both configurations on the same Intel Xeon host with FMA3 enabled.
Both builds passed all five cases twice. The Lua event streams were identical.
The first recorded controller difference was in the stock DG flight-path
slope at tick 34. Debug returned 0.095827486401893064 and Release returned
0.095827486401892994. The first finalized elevator difference followed at tick
35. The added diagnostics left every Debug vessel-state and control trace
byte-identical to the previous run. The exact cross-build control check remains
open and the Lua references have not been frozen.

The native Lua build also compiles the complete original `lua_vessel_mtd.cpp`,
including the vessel method registration table and the Lua vessel MFD2
callbacks. The source check compares every method body and registration with
the historical Windows source after accounting for SDK type names and the
case-insensitive string comparison. Its vessel and MFD method symbols are
available from the native cockpit engine. Executing the bindings still
requires the remaining interpreter implementation and module loader.

Both the native interpreter startup and the stock DG Lua initialization callback
now address files through the production resource index. Lua's `dofile` and
`loadfile` resolve the original `Script` directory case-insensitively and accept
backslashes. Other paths retain the Lua library's normal behavior. Local tests
with the pinned Lua VM compiled the original startup and AAP files, executed
the stock strict-mode script, preserved Lua multiple returns, and rejected a
missing stock file and an attempted traversal. The DG Lua source compiles as a
native object. Running AAP jobs against a live native DG still requires the full
Orbiter interpreter and the stock vessel module.

The native cockpit build compiles the 15 original DG subsystem sources used
by the Windows vessel, including the DG-S scramjet and the AAP panel. A local
relocatable link of those objects and the stock instruments left four Orbiter
script calls and five methods on the main DeltaGlider class to resolve. The
subsystem archive alone does not load a vessel or execute its autopilot.

The shared panel, VC and HUD SDK functions call the original Pane, and the
scenario SDK shares the original readers, writers and floating-point format
with Windows. A 60-frame ShuttlePB run exercised HUD mode switching, docking
receiver selection, brightness and subsystem scenario round trips. DG panel
click areas and VC rendering still need verification on the actual DG vessels.

The cockpit engine now builds the original main vessel class, DG Lua callbacks,
stock instruments and 15 subsystems into `NativeModules/Vessel/DeltaGlider.so`.
The shared module links with `--no-undefined`. Native DG and DG-S activation
from their original atmospheric scenario states reaches the AAP constructor.
Both launches currently stop on the missing `Plugin/LuaInline.so`. The engine
loads that provider on demand and dispatches script work after vessel post-step
callbacks. The original LuaInline environment list and module entry compile.
Finishing the main interpreter library is required before either flight can run.
The native scenario reader also bounds skin names and validates passenger seat
numbers. The Windows scenario editor pages remain in the Windows build.

The paired Windows capture at 1f71edba traced the first controller difference
to the vertical component of the horizon airspeed vector supplied to Lua.
At tick 34 Debug returned 29.924461703343582 m/s and Release returned
29.92446170334356 m/s. The horizontal components and `xz` were identical.
The next capture records Earth rotation, equatorial position and velocities
in global, planet-local and horizon frames immediately before Lua runs.
The exact cross-build control requirement is still open.
[Paired original Windows capture](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41555762691)
