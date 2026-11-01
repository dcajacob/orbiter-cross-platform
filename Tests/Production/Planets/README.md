# Production planet and base extraction

The shared library now compiles the original `Planet`, `Base`, `BaseObject`
implementations, surface navigation/hull geometry, and `VesselBase` surface and
contact calculations. Atmosphere calls reach the actual stock SPICE atmosphere
module through explicit services. Windows retains its actual SDK types and
legacy Direct3D draw methods; Linux compiles the CPU geometry without them.

This is component coverage. It does **not** create a native application,
`PlanetarySystem`, `Vessel`, camera, renderer, or playable scene.

`Observe.cpp` loads the real Sun first, then Earth, Moon and Mars, their actual
modules, gravity models, terrain, and all 39 stock surface bases. It exports
their actual visual/shadow/collision CPU mesh geometry and checks vessel surface
altitude transforms. Twenty load/unload cycles exercise resource lifetime.
Headless mesh loads explicitly retain CPU texture identities without GPU handles.
The verifier checks frozen kernel/gravity/archive hashes and records source
configuration hashes. No scenario or asset is replaced with proxy content.

From the checkout, after preparing the existing verified data directories:

```sh
cmake -S Src/Orbiter/Production -B out/production-boundary \
  -DCMAKE_BUILD_TYPE=Debug -DORBITER_BUILD_NATIVE_CELESTIAL_MODULES=ON
cmake --build out/production-boundary --parallel 2
ctest --test-dir out/production-boundary --output-on-failure
python3 -B Tests/Production/Planets/verify.py \
  --executable out/production-boundary/production_native_planet_observer \
  --modules out/production-boundary/NativeModules \
  --data out/native-celestial-data --planets out/archive-data \
  --output out/native-planets-verification-debug
```

The terrain workflow runs the same component probe on Windows MSVC and Linux
GCC, Debug and Release, alongside the unchanged frozen terrain comparisons.
The full Windows application, SDK, behavior and real-client image gates remain
required for this extraction. Hosted results are distinct from local results.

Local geometry/lifetime verification exposed original resource issues: a
zero-length mesh texture allocation, missing `Tank` cleanup, generated base
mesh/shadow ownership, and headless static texture-name cleanup. Cleanup now
releases owned CPU buffers and keeps borrowed graphics surfaces with their
owner. Empty base-object copies are guarded. The hull routine uses separate
aligned typed buffers instead of storing pointers in an unaligned byte buffer;
its sorting and geometric calculation order stay unchanged.

`surface_source.py` conserves original planet wind/force/update calculations,
all base-object geometry/dynamics, vessel surface/contact calculations,
orthodome calculations and texture name IDs. The original numerical tolerances
and frozen Windows references are unchanged.
