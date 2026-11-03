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
