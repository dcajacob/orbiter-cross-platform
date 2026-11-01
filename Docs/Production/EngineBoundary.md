# Production engine extraction

Phase 3 is in progress. The complete production engine does **not** yet build
on Linux. `orbiter_production_boundary` is an internal shared library containing
the first extracted production services; it is not a native Orbiter executable.
The restricted POC session and all original reference files remain unchanged.

`WorldOwner` now owns the production `Camera` and `PlanetarySystem` lifetimes.
Windows creates the original classes through `WindowsWorldFactory`; the existing
application globals are non-owning aliases. Replacement keeps the original new-
camera-before-new-world order, and teardown releases the camera before the world.
Normal session close releases both before graphics/plugin shutdown. Application
destruction also releases any remaining world before unloading modules. Partial
initialization failures release owned resources and propagate their errors.
Window, panel and input lifetime remain in the Windows host.

The internal native bootstrap loads a module with the platform's actual dynamic
loader (`dlopen` on Linux, `LoadLibraryExW` on Windows), checks its descriptor,
architecture, kind, SDK build and C++ toolchain/standard-library tag, then calls
explicit initialization. Shutdown runs before unloading the library. Missing
libraries/entries, incompatible builds and failed initialization produce errors.
The existing Windows SDK and its legacy DLL registration path are unchanged.

The generated build identifier pairs a shared engine library with its SDK headers;
it includes a persistent per-build token, source/header hashes, compiler settings
and configuration. Modules must consume that build's CMake target and generated
header. Independently configured engine builds, Debug/Release configurations and
incompatible compiler/STL settings are not interchangeable. This is an internal
bootstrap contract, not a released native SDK or arbitrary C++ ABI compatibility.

A loadable fixture constructs an actual production `Body` through the same shared
library and services as its host. Tests cover twenty module initialize/shutdown/
unload cycles and reject invalid ABI/build/toolchain/kind/size descriptors,
missing entries and initialization failure. It is not a stock vessel module and
does not satisfy the real-world or twenty-real-graphics-session gates. Native
vessel, celestial-body, atmosphere and graphics interfaces still need extraction.

The portable ownership tests cover twenty token lifetimes, replacement, empty
worlds, failed factories and destruction. They do not construct a native world
and do not satisfy the twenty-real-session graphics gate. `PlanetarySystem` and
`Camera` implementations still need platform extraction before a Linux factory
can create them.

The first extraction moves `Orbiter::UpdateWorld` and `EndTimeStep` ordering
into `Production/Session.cpp`. Windows Orbiter invokes these functions through
`WindowsSessionServices`, which calls the original `PlanetarySystem`, module,
vessel, camera, pane and graphics implementations. Live running/playback/update
flags retain their original callback semantics. Input, frame timing policy and
rendering remain at their existing positions in the application loop.

The next component is the original `Body` class, compiled into the same shared
library on Windows and Linux. Its state buffers, coordinate transforms and
finalization methods retain the production implementations. Configuration path,
load-status, size notification, visual notification and debug-assert policies
are explicit `BodyServices`. Windows binds those services to the existing
application; an unbound native world fails. SDK-facing Windows integer/handle
types are checked for exact type identity in the adapter. `Vecmat`, `TimeData`
and configuration primitives now have one compiled implementation per process
in this library, including the unchanged POC regressions that consume them.
Numeric configuration readers use call-local scratch storage in place of the
application configuration file's global buffer.

`RigidBody`, all ten existing RK/symplectic propagators and the existing Encke
code now compile in this library as well. `RigidBodyServices` supplies the
original physics settings, simulation clock, reference-body states and gravity
queries. The Windows implementation delegates to the actual `PlanetarySystem`
and `CelestialBody`; no force model or integrator is replaced. The numerical
configuration structure is shared without pulling in application or SDK UI
headers. Optional allocation diagnostics remain a host policy.

An independent inertial/free-spin test runs each propagator for 6,000 quarter-
second steps twice, with the same seed and finalized sampling. It checks the
analytical translation/rotation and energy/angular-momentum invariants within
the existing budgets. Each run writes 601 samples. The hosted matrix compares
all ten production-class traces across Windows/Linux Debug/Release, separately
from the original two-body goldens. This empty-force-field test has no primary,
ephemerides or vessel module and is not a runnable production scenario.

The original MSHX1 reader and angle-weighted normal calculations now have shared
implementations without Windows or Direct3D headers. The Windows sink retains
the existing internal mesh and SDK representations and performs real renderer
texture acquisition. The native sink owns CPU vertex/index/material records and
texture names/flags. Group order, material/texture inheritance, UVs, static/wrap
flags and user flags are retained. Native CPU loading does not allocate GPU
resources. Three-coordinate untextured vertices and CRLF input are supported,
as required by the original stock meshes. Negative geometry counts, truncated
geometry and invalid indices fail rather than being dereferenced.
Counts and triangle indices are range-checked before narrowing, including
oversized decimal input that would wrap a 16-bit or 32-bit destination. Valid
signed-positive index syntax and all original stock meshes remain supported.

The shared reader uses the SDK's actual `NTVERTEX`, `COLOUR4` and `MATERIAL`
records from `OrbiterMeshData.h`. Their declarations are extracted verbatim from
the Windows SDK. The source audit reconstructs the original SDK header around
that extraction and rejects other changes to its declarations. Independent
layout checks enforce all field offsets, sizes and alignment on both platforms.
This provides shared value records, not a native vessel/module SDK.

The actual production `Mesh` and `MeshManager` now compile in the shared library.
Geometry, group edits, transforms, normals, materials and cache behavior use
their original calculations. The disabled Direct3D vertex-buffer field and
unimplemented device-rendering functions are removed from the CPU object; GPU
buffers remain renderer-owned. Textures are opaque host resources, with declared
source names/flags retained as CPU metadata. File access, texture acquisition,
release, allocation diagnostics and error reporting use an explicit host callback
table. The Windows table calls the original application and graphics client.
Default mesh flags are initialized to zero instead of exposing uninitialized
memory. The SDK material API now accesses actual `MATERIAL` storage directly.

Windows adapters check every group field's type and offset against the SDK,
as well as every edit-mask value. The SDK edit adapter retains the original
out-of-range behavior and only reads fields selected by its flags. Tests load
the real stock ShuttlePB through `MeshManager`, verify deep geometry copies,
indexed edits, transforms, material ownership, source identities, caching,
missing-resource failures and host resource callbacks. These CPU tests do not
substitute for actual graphics-client execution.
Partially parsed meshes are rejected before caching and released even when the
host's error callback throws.

`ResourceResolver` indexes an explicit resource root, normalizes stock Windows
separators and ASCII case, preserves actual filename spelling, and rejects
conflicting file **or directory** aliases. Missing resources, paths escaping
the root and symlinks fail explicitly. The production Windows configuration
path adapter is still unchanged; integrating this resolver throughout the world
loader remains work for the next extraction.

The original `State` environment/focus metadata parser and writer also compile
in the library. Native calls take an explicit default MJD, current MJD/focus,
and file path or input stream. Windows call forms remain application adapters
that supply the original system-clock conversion, test observation hook and
focus object. MJD/JD/Julian-epoch interpretation and ten-decimal MJD save precision
are unchanged. The original section finder uses call-local scratch storage;
the original CSS colour table/parser is shared without device types. An absent
splash colour starts at zero rather than uninitialized memory.

Tests read all 157 original stock environment/focus headers with a recorded
default epoch, plus CRLF, date-format, missing-file and save/reload cases. A sorted,
locale-independent metadata manifest is compared exactly across the four hosted
platform/configuration builds. This is metadata coverage only: vessel records,
modules, camera, instruments and world initialization are not exercised by that
test and remain part of the production scenario gate.

Build this boundary without a display, SDK, renderer or asset download:

```sh
cmake -S Src/Orbiter/Production -B out/production-boundary -DCMAKE_BUILD_TYPE=Debug
cmake --build out/production-boundary --parallel 2
ctest --test-dir out/production-boundary --output-on-failure
```

The tests exercise running/paused frames, callback-induced running changes,
deferred deletion and finalized sampling, actual stock mesh records, normal
generation, resource lookup and explicit failure paths. The pinned empty
`Meshes/Hyperion.msh` placeholder is required to fail; no geometry is substituted.
These tests also run in the existing Linux GCC / Windows MSVC Debug/Release
matrix and in the full Windows application build.
The production Body test also checks configuration initialization, creation
during an update, publication of finalized state and actual service routing.

Extraction changes are declared explicitly in
`Tests/Production/phase3-extraction.lock.json`. The audit first proves that the
accepted observation-only source still preserves the original production bytes,
then checks the declared extraction files and rejects other production/SDK
changes. This ledger is a source-review aid; it does not establish behavioral
equivalence. The frozen two-body, production orbit/propulsion, fourteen behavior
cases and real-client references supply that separate runtime gate.

The [preserved verification reports](../../Tests/Production/Verification/EngineBoundary/README.md)
record accepted component sources, hosted runs and original artifact hashes;
local Linux results are reported separately.

Before extracting nonspherical gravity, the [Pines observation protocol](../../Tests/Production/Gravity/README.md)
captures the unchanged Windows implementation against locked stock Earth/Moon
coefficients and an independent J2 check. The accepted reference from hosted
run 41280522652 has identical traces in standalone/application Debug/Release
builds, and is frozen before extracting that source. Its force-query budgets
supplement the unchanged orbit/contact references.

The real-client workflow now builds the **current** production application and
SDK together, rather than reusing the pre-extraction application. It compares
Debug/Release against each other and both against the accepted Phase 2 state,
callback, object/asset, camera and image evidence. Numerical, one-pixel and SSIM
budgets are unchanged. Neither inherited disabled workflow is modified.

Remaining Phase 3 work includes full session/platform lifetime extraction,
configuration/scenario/resource integration, platform service separation for
`CelestialBody`, `Vessel` and `Camera`, instrumentation dependencies and the source-built native SDK/module
boundary. These shared components do not yet satisfy the Phase 3
exit gate that Linux builds the production engine and its authoritative objects.
