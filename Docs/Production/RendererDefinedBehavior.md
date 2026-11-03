# Fully instrumented renderer and planet initialization

Expanding instrumentation to C and C++ in both the engine and renderer exposes
two undefined accesses after the native Lua guards. Earlier lifetime runs used
the sanitized engine with an uninstrumented renderer; their recorded results
remain scoped to that setup. The new builds instrument the C/C++ sources
compiled by the engine and renderer builds, including Lua, GLFW and fetched
renderer dependencies. Prebuilt CSPICE and system libraries retain their
existing builds.

The first retained failure is `Scene.cpp:544`: the distance-sorted celestial
list stores a `vStar` through an invalid `vPlanet*` cast. The list now stores
their actual common `vObject*` base. The existing type check still precedes
planet-specific label activation. Object selection, camera distances, sorting,
virtual rendering calls and their order are unchanged.

The next run stops at `VPlanet.cpp:98` while reading the planet's cloud
microtexture property. The config-based `Planet` constructor sets this flag
only when a valid `CloudMicrotextureAlt` entry exists. Stock Triton has clouds
and omits that entry. The flag now starts false, matching the other constructor;
valid settings retain the original parsing and enable it. No SDK field, type,
layout, calculation or simulation ordering changes. The source audit accepts
exactly this initialization repair and compares all other bytes against its
previous numerical source. Controls reject missing, altered and repeated
initialization.

The read-only SDK observer in `Tests/Production/PlanetDefaults/` checks Earth
and Venus remain enabled, while Triton and the Moon have a defined false
default. It collects 240 observations over 60 full presentations and normal
context teardown. The hosted native workflow is configured to repeat this
check in all four build/CPU profiles and retain the captures.

The fully instrumented DG panel flow now reaches actual Wayland keyboard,
focus and mouse/camera input, presents 636 frames and deletes the graphics
context. It still fails at process exit: unsuppressed LeakSanitizer reports
273,300 bytes in 6,411 allocations. Of these, 273,188 bytes in 6,409 allocations
have Fontconfig in their stacks through the GTK/Pango decoration path. The
remaining two 56-byte allocation callers map into the loaded system Gallium
library. This address classification is evidence, not a suppression or a
passing lifetime result.

A [minimal pinned GLFW window](../../Tests/Production/WindowDecorationLifetime/README.md)
reproduces the decoration leak without Orbiter or mipmaps. Its explicit builtin
decoration control is clean. Production decoration selection and system
libraries remain unchanged; the precise dependency cleanup and the complete
Wayland sanitizer gate remain open. The earlier isolated Mesa allocator
candidate is documented separately and was not selected in this system-driver
run.

[RendererDefinedBehaviorVerification.json](RendererDefinedBehaviorVerification.json)
records the runtime identities, source hashes, preserved Windows comparisons,
actual property observations and retained failures. Original reference bytes
and all acceptance budgets are unchanged. The local evidence bundle preserves
all six fresh engine/module sets, exact intermediate sources, original Lua
ZIPs and camera observations, normal regressions and sanitizer failures. Every
archive payload hash was rechecked after compression. Remote preservation
remains open. Phase 6 remains in progress.
