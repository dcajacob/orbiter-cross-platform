# Real Windows OpenGL client

`OVP/OGLClient` builds a separate MSVC `OGLClient.dll` implementing the current
Windows `oapi::GraphicsClient` interface. Orbiter loads and registers it normally;
Win32/WGL owns the window and context. The renderer consumes the production
world, camera, mesh parser, materials, textures, visual notifications and original
vessel modules. Its GLM types and GPU resources stay private. The donor's SDK,
application and numerical-type changes are excluded.

The accepted hosted integration is [run 41198786277](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41198786277),
renderer source `21f92f44f3afd0c3ca8a704edd4ef2ce8e10c6a0`. Both MSVC x64 Debug
and Release load the original Sol system, config-driven `ProjectAlpha_ISS` and
the source-built `ShuttlePB.dll`. This is the real Windows external-view client
milestone. Production Linux engine extraction is the next phase.

[Frozen evidence](../../Tests/Production/ClientReference/README.md) retains the
canonical capture, reports, traces and original artifact digests. Large original
ZIPs and logs live in versioned release storage.

## Measured integration

Each configuration executes two fresh processes, each with 60 original physics
ticks of 0.25 seconds, and reads back the finalized tick-50 frame at 12.5 seconds.
This reduced engineering fixture does not replace the stock scenario corpus or
the existing frozen 6,000-second numerical references.

| Evidence | Result in both configurations |
| --- | --- |
| Real window and viewport | 1280 × 720 |
| Actual loaded renderer | Mesa 26.2.6, llvmpipe / LLVM 23.1.4, OpenGL 4.6 core |
| Window lifecycle | 60 completed renders/presents; WGL context deletion succeeds |
| ISS CPU mesh | `ISS\ProjectAlpha_ISS`, 42 groups, 36 materials, 36 textures |
| ShuttlePB CPU mesh | `ShuttlePB`, 7 groups, 2 materials, 2 textures |
| Observed vessel geometry submissions by sample | ISS 378; PB 56 |
| Earth surface | 466 textured tile submissions; 9,225,216 inflated surface-archive bytes |
| Visual lifetime | Actual registration and unregistration, including Earth, ISS and PB |
| Repeated images and numerical traces | Byte-identical within each configuration |
| Frozen production state comparison | Zero measured position, velocity, attitude, angular-velocity and MJD error |
| Hosted Debug/Release comparison | Zero state/landmark error; identical images, SSIM 1.0 |

The test verifies actual loaded DLL paths/hashes, the stock mesh files and loaded
texture/archive hashes. The Release application retains its original zlib DLL;
all Mesa dependencies' named zlib imports must be satisfied by its actual C
exports. Other application/Mesa DLL conflicts fail. Debug uses its original
`zlibd1.dll` and the separately pinned Mesa zlib runtime.

The comparison uses the existing orbital and propulsion budgets unchanged.
Projected Earth/ISS/PB object centres must agree within one pixel. Full RGB image
SSIM must be at least 0.98, using an 11×11 Gaussian window, sigma 1.5, population
covariance and the valid image crop. No overlay masks, image resizing or colour
changes are applied. FPS is disabled and simulation timing is fixed. Raw RGBA
readbacks are retained beside lossless PNG conversions.

## Reproduce

Use native Windows with the recorded MSVC/Windows SDK and DirectX June 2010
header dependency. The workflow verifies all original application/SDK source
files against `06d8989823c59e651061d409425c19ec71360bfa` before reusing a runtime.
It caches the source-built SDK/runtime, can obtain the original retained Debug
artifact, and rebuilds the pinned original source when a retained runtime is
unavailable. A fresh Release rebuild exercises this path. Existing application
tests and the locked dependency-commit audit must pass before packaging it.
Artifact retention is therefore not the sole way to reproduce the executable.

Given the verified same-build runtime at `out/production-app` and Python 3.14:

```powershell
cmake -S OVP/OGLClient -B out/opengl-client -G Ninja `
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5 `
  -DCMAKE_EXPORT_COMPILE_COMMANDS=ON `
  -DORBITER_TEST_RUNTIME="$pwd/out/production-app" "-DDXSDK_DIR=$env:DXSDK_DIR"
cmake --build out/opengl-client --target OGLClient --parallel 2
cmake -S Tests/Production/BehaviorBuild -B out/driver -G Ninja `
  -DCMAKE_BUILD_TYPE=Release -DORBITER_TEST_RUNTIME="$pwd/out/production-app"
cmake --build out/driver --parallel 2
python Tests/Production/prepare_data.py --archive out/data-cache/Orbiter-x64.zip --destination out/production-data
python Tests/Production/prepare_data.py --lock Tests/Production/standard-planets.lock.json `
  --archive out/planet-cache/Orbiter2016.zip --destination out/standard-planets
python Tests/Production/stage_mesa.py stage --cache out/mesa-cache --destination out/mesa-runtime
python Tests/Production/Client/run_client.py --orbiter out/production-app/Orbiter.exe `
  --data out/production-data --planets out/standard-planets --mesa out/mesa-runtime `
  --configuration Release --output out/client-execution
```

Output directories must be new. See [the complete hosted recipe](../../.github/workflows/production-client.yml)
for the original application build, dependency hashes, compiler configuration and
Debug/Release artifact comparison. Data provisioning uses the existing locked
packages and never downloads vessel DLLs over the source-built modules.

## Deliberate scope

This page records the Windows adapter's integration gate. The shared renderer
also runs through the extracted Linux production core and internal client
contract; see [native external-view evidence](NativeExternalView.md). The earlier
`orbiter-native` viewer remains a separate portability POC.

The integration uses a fixed initial viewport and an external camera. Floating
ImGui platform windows are explicitly disabled and logged; dialogs use the main
window. Full surface-flag semantics, cockpit/HUD/MFD instrument validation, VC
picking, all animation/edit callbacks, visual-feature completeness, resize/high
DPI, twenty repeated sessions in one process, the stock 157-scenario corpus and
hardware performance remain later gates. Two fresh processes do not establish
repeated-session resource reuse. Missing required fixture assets/modules fail.

The isolated import retains [donor attribution and dependency notices](../../OVP/OGLClient/ATTRIBUTION.md).
Repairs include current SDK callback signatures and visual-event contexts,
field-wise material conversion, real HBITMAP/surface loading, wide text,
production star catalog access, camera conventions, signature-based texture
loading, synchronous tile loading on the GL thread, fixed-width archive records
and 64-bit seeks, viewport state, alpha-state synchronization, current ImGui
frame finalization, real mesh identities and duplicate index-buffer deletion.
No production propagation formulas, public Windows SDK types, module exports or
SDK virtual ordering were changed for this renderer.
