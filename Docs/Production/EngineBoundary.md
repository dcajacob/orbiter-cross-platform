# Production engine extraction

Phase 3 is in progress. The complete production engine does **not** yet build
on Linux. `orbiter_production_boundary` is an internal shared library containing
the first extracted production services; it is not a native Orbiter executable.
The restricted POC session and all original reference files remain unchanged.

The first extraction moves `Orbiter::UpdateWorld` and `EndTimeStep` ordering
into `Production/Session.cpp`. Windows Orbiter invokes these functions through
`WindowsSessionServices`, which calls the original `PlanetarySystem`, module,
vessel, camera, pane and graphics implementations. Live running/playback/update
flags retain their original callback semantics. Input, frame timing policy and
rendering remain at their existing positions in the application loop.

The original MSHX1 reader and angle-weighted normal calculations now have shared
implementations without Windows or Direct3D headers. The Windows sink retains
the existing internal mesh and SDK representations and performs real renderer
texture acquisition. The native sink owns CPU vertex/index/material records and
texture names/flags. Group order, material/texture inheritance, UVs, static/wrap
flags and user flags are retained. Native CPU loading does not allocate GPU
resources. Three-coordinate untextured vertices and CRLF input are supported,
as required by the original stock meshes. Negative geometry counts, truncated
geometry and invalid indices fail rather than being dereferenced.

`ResourceResolver` indexes an explicit resource root, normalizes stock Windows
separators and ASCII case, preserves actual filename spelling, and rejects
conflicting file **or directory** aliases. Missing resources, paths escaping
the root and symlinks fail explicitly. The production Windows configuration
path adapter is still unchanged; integrating this resolver throughout the world
loader remains work for the next extraction.

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

Extraction changes are declared explicitly in
`Tests/Production/phase3-extraction.lock.json`. The audit first proves that the
accepted observation-only source still preserves the original production bytes,
then checks the declared extraction files and rejects other production/SDK
changes. This ledger is a source-review aid; it does not establish behavioral
equivalence. The frozen two-body, production orbit/propulsion, fourteen behavior
cases and real-client references supply that separate runtime gate.

The real-client workflow now builds the **current** production application and
SDK together, rather than reusing the pre-extraction application. It compares
Debug/Release against each other and both against the accepted Phase 2 state,
callback, object/asset, camera and image evidence. Numerical, one-pixel and SSIM
budgets are unchanged. Neither inherited disabled workflow is modified.

Remaining Phase 3 work includes production world/session ownership and teardown,
configuration/scenario/resource integration, body/vessel/camera platform service
separation, instrumentation dependencies and the source-built native SDK/module
boundary. A shared coordinator and CPU asset reader do not satisfy the Phase 3
exit gate that Linux builds the production engine and its authoritative objects.
