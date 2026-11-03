# Native Delta-glider integration

Phase 6 requires the original Delta-glider and DG-S source modules, systems,
meshes, 2D and virtual cockpits, and Lua-backed AAP. Native vessel execution
and cockpit acceptance are still in progress.

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
traces. The next capture uses one Windows host and records the stock script's
intermediates without advancing the interpreter or changing its arithmetic.
The exact cross-build check remains in force.

The native Lua build also compiles the complete original `lua_vessel_mtd.cpp`,
including the vessel method registration table and the Lua vessel MFD2
callbacks. The source check compares every method body and registration with
the historical Windows source after accounting for SDK type names and the
case-insensitive string comparison. Its vessel and MFD method symbols are
available from the native cockpit engine. Executing the bindings still
requires the remaining interpreter implementation and module loader.
