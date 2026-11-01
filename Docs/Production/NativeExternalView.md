# Native production external view

A real native production scene now runs on the laptop's Intel/Mesa GPU under
Wayland. It uses the original `PlanetarySystem`, `Body`, `RigidBody`, `Vessel`,
`Camera`, `Session` and `WorldOwner`; actual Sol/SPICE and J71G; stock ISS assets;
and the source-built ShuttlePB through the checked native SDK. The independently
built OpenGL module uses the same scene, meshes, materials, textures, animations
and planet tile implementation as the accepted Windows OpenGL client.

This is a narrow external-view delivery, not the stock-playable release. The old
`orbiter-native` remains a separate POC. No restricted `SimulationSession`,
procedural replacement vessel, replayed trace, Windows DLL, or Wine supplies this
production view.

## Local evidence and controls

On the current Ubuntu 26.04 laptop, GCC Debug, Mesa Intel Graphics (PTL), OpenGL
4.6 / Mesa 26.0.8: two 60-frame runs produce identical state and numerical/scene
traces and identical image bytes. At 1280×720, each full image has SSIM
**0.9862598209696377** against the unchanged Windows reference (minimum **0.98**,
no masks). Camera values and projected Earth/ISS/PB landmarks agree exactly.
All recorded vessel position, velocity, attitude, angular velocity, MJD,
mass and fuel differences are zero against the frozen Windows scene states.
The manifest records 484 mesh draws and 660,483 mesh indices at capture,
real textured Earth/Moon archive reads, actual module paths/hashes, and normal
visual registration, unregistration, 60 presentations and context teardown.

These are local hardware results. Hosted Ubuntu 24.04 Debug/Release and current
Windows SDK/application/real-client validation are separate CI gates. The
workflow `native-production-client.yml` executes real windows using Xvfb and
Mesa llvmpipe; its report verifies the actual reported software renderer and
loaded library paths. A successful compile does not count as graphics execution.

For the prepared laptop build:

```sh
Tests/Production/NativeScene/run-local.sh
```

Right-drag orbits the original camera, the wheel zooms, and Escape closes the
window. Preview starts paused. `--run` advances the production simulation with a
fixed step per frame for this engineering host. Keyboard/joystick flight input,
cockpit/HUD/MFD operation, Lua, playback, sound, general scenario compatibility,
20 sessions in one application process, X11 laptop validation and release
packaging remain open. Empty cockpit redraw notifications are retained as
pending flags; no panel or virtual-cockpit areas are registered in this view.
Requests for unsupported cockpit operations fail explicitly.

The launcher uses a copied build under `out/native-production-preview` so ongoing
compilation cannot overwrite a live application's mapped libraries. This is a
development preview with explicit asset roots, not a relocatable release bundle.

## Reproduce

Prepare the unchanged data profiles using `prepare_native_data.py` and
`prepare_data.py`, then stage source/data assets with
`Tests/Production/NativeScene/prepare.py`. The development provisioner verifies
every locked data hash and Windows-style installation overlay order; it omits
the already excluded restricted font. It is not the final resumable asset installer.

```sh
cmake -S Src/Orbiter/Production -B out/native-vessels -DCMAKE_BUILD_TYPE=Debug \
  -DBUILD_TESTING=OFF -DORBITER_BUILD_NATIVE_VESSELS=ON \
  -DORBITER_BUILD_NATIVE_CELESTIAL_MODULES=ON
cmake --build out/native-vessels -j4
python3 -B Tests/Production/NativeScene/dependencies.py --cache out/ogl-native-deps
cmake -S OVP/OGLClient/Native -B out/production-ogl-native -DCMAKE_BUILD_TYPE=Debug \
  -DORBITER_ENGINE_BUILD="$PWD/out/native-vessels" \
  -DORBITER_RENDERER_DEPENDENCIES="$PWD/out/ogl-native-deps"
cmake --build out/production-ogl-native -j4
python3 -B Tests/Production/NativeScene/prepare.py --data out/production-cache/data \
  --planets out/archive-data --destination out/native-scene-resources
python3 -B Tests/Production/NativeScene/verify.py \
  --executable out/native-vessels/orbiter-production --assets out/native-scene-resources \
  --data out/native-celestial-data --modules out/native-vessels/NativeModules \
  --planets out/archive-data --configuration Debug --output out/native-production-scene-verified
```

For a Wayland-only development build without XRandR development headers, add
`-DGLFW_BUILD_X11=OFF` to renderer configuration (the local preview uses this).
CI uses X11/Xvfb with `-DGLFW_BUILD_WAYLAND=OFF`. These are window adapters, not
changes to world/numerical code. Install the matching development packages to
build both backends together.

## Boundaries and compatibility

The Windows `GraphicsClient`, exports, SDK field types and virtual ordering are
preserved. Source audits conserve the original camera, drawing and celestial
sphere calculations. Native SDK compatibility means the exact same build and
C++ toolchain; the loader checks that before initialization.

Renderer implementation symbols are hidden on ELF, including its private
`ZTreeMgr`, which has a different layout from the engine's independent terrain
archive reader. The export regression test prevents accidental interposition.
Both implementations retain their own lifetime and data access. Stock texture
lookup resolves case/separators before image decoding; DDS and misleading BMP
extensions use their actual signatures. GPU resource types remain renderer-private.

Required ISS/PB classes, module capabilities, meshes and textures fail explicitly
when missing. Existing optional distant small-body shape probes retain the
original SDK load behavior. They do not substitute for required fixture objects.
The host rejects application plugins, scripts and cockpit scenarios outside its
current scope. All immutable references and numerical/image budgets are unchanged.
