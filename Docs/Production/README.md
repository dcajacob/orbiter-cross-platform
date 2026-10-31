# Production native Orbiter release

The native stock release is **not complete**. `orbiter-native` is a portability
POC using the restricted `SimulationSession` and procedural geometry. Its
[accepted evidence](../../Tests/Portable/ClientVerification/README.md) remains
valid for that scope. It does not count as production engine/client integration.

## Frozen scope and starting point

The release uses the existing `PlanetarySystem`, `Body`, `RigidBody`, `Vessel`,
`Camera`, scenario, terrain, collision and instrumentation implementations.
Production extraction must preserve callback, update, deletion, finalization,
time, camera/panel and graphics ordering. The restricted session remains a
regression target, not the foundation of the production application.

Production source is frozen at
`38b7c627878ea893390675616897071f8bb8e90f` (upstream ancestry retained).
[The source lock](../../Tests/Production/production-source.lock.json) records 425
source/config/scenario SHA256 hashes, all 157 original scenarios and their vessel
identities, 101 module build files, 70 named graphics callbacks and 500 tracked
asset Git blobs. These are inventory entries, not claims that they have run.

The real renderer donor is pinned at
`ad96494482e6101afebf1c635e4e1f542623b51d`. Import only reviewed renderer files
with attribution and licenses. Do not import the fork's SDK, math types or
application changes. Preserve Windows SDK layouts, exports and virtual ordering.
Use a Windows `GraphicsClient`/Win32/WGL adapter and a separate Linux module/GLFW
adapter over one rendering implementation. Renderer types stay private.

Linux x86-64, Ubuntu 24.04 minimum, stock modules rebuilt from source with the
same native SDK/toolchain, and SPICE with matching kernels define the release.
Unmodified Windows DLLs, proprietary hardware integrations, Windows auxiliary
tools and full D3D9 visual parity are deferred. No Wine or visual proxy objects
may satisfy a production acceptance case.

## Capability and dependency inventory

| Capability | Current native implementation | Release requirement / dependency |
| --- | --- | --- |
| Vecmat, elements, two-body RK4 | Verified restricted fixtures | Preserve frozen references unchanged |
| Window/input/procedural view | POC only | Native production window, input and real graphics client |
| Production world and session | Unsupported | Existing lifecycle, shared engine library and platform services |
| SPICE Solar System | Unsupported | Current `Src/Celbody/SPICE`, CSPICE, `orbiter.bsp`, TLS/PCK and coverage verification |
| Native module ABI | Unsupported | Source-built vessels, celbodies, atmospheres, plugins; version/toolchain check |
| Real stock meshes/materials/animations | Unsupported | Existing CPU mesh parser separated from D3D resources; actual group identities |
| Planet tiles and elevation | Unsupported | Portable fixed-width archives, 64-bit offsets; engine contact queries independent of visibility |
| Resource resolution | POC fixture paths only | Indexed Windows-separator/case-insensitive resolver with ambiguous alias errors |
| Texture loading | Unsupported in production | Signature-based DDS DXT1/3/5 and uncompressed formats; BMP in `.dds` files |
| Propulsion, RCS, atmosphere, docking, contacts | Unsupported in native application | Preserve original systems; production references before extraction |
| HUD/MFD/2D panels/VC/Sketchpad | Unsupported | Original instruments, redraws, surfaces, fonts/TextW, picking and interaction |
| Lua, tutorials, playback, editor, audio | Unsupported | Bundled modules/scripts and portable views over existing logic |
| Installation and assets | POC fixture bundle only | Relocatable runtime, native SDK, verified/offline/resumable separate asset installer |

[Graphics callback inventory](graphics-capabilities.csv) explicitly records
unsupported native callbacks and known donor defects. `clbkLoadSurface` and
`clbkMeshMaterial` terminate the donor process; TextW aborts; surface flags and
material layout copying need repair. Call coverage must establish which optional
callbacks the pinned stock corpus actually requires. Silent no-op success is
not an implementation. No donor code has yet been imported.

Other dependencies: DirectX June 2010 and Windows SDK/MSVC for preserved Windows
builds; Lua and LuaFileSystem/Penlight; atmosphere modules; miniaudio/XRSound;
mesh/texture/gravity data; renderer dependencies including GLAD, SOIL2, NanoVG,
libnsbmp and fonts. License closure must accompany selective renderer import.
Core MIT and D3D9 LGPL components retain their existing licenses. The pinned Mesa
runtime lock lists package licenses and staging preserves the distributed license
files. A complete redistributable stock-data license manifest is still required.

## Ordered delivery gates

| Phase | Delivery | Status / exit condition |
| --- | --- | --- |
| 0 | Honest POC labeling, scope and inventories | Source inventory implemented; no production runtime claim |
| 1 | Production Windows references and hosted WGL | Bootstrap implemented; runtime evidence and production references required |
| 2 | Real Windows OpenGL client | Not started; normal registration/lifecycle, actual Sol ISS/ShuttlePB meshes/assets and scene manifest |
| 3 | Production engine/platform boundary | Not started; Windows reference/ABI/lifecycle regression gates after every extraction |
| 4 | Native real world/external client | Not started; SPICE and actual ISS then native ShuttlePB; cross-platform state/scene parity |
| 5 | Usable flight and interaction | Not started; propulsion, fuel, all RCS axes, autopilot, docking, contact, persistence |
| 6 | Cockpit and Delta-glider | Not started; real DG/DG-S 2D/VC, HUD/MFDs, animations and controls |
| 7 | Practical stock experience | Not started; remaining modules, Lua, audio, scenarios, settings and input configuration |
| 8 | Packages and release acceptance | Not started; clean install outside checkout, data installer, SDK, all automated and hardware gates |

Later phases cannot substitute for failed earlier gates. Use the narrower labels
real Windows client, native production core, native external view and
cockpit-capable build until Phase 8 passes.

## Phase 1 reproducibility

```sh
python3 Tests/Production/inventory.py --verify
```

On native Windows, from an MSVC x64 developer shell:

```powershell
cmake -S Tests/Production -B out/wgl -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build out/wgl
python Tests/Production/mesa_runtime.py stage --cache out/mesa-cache --destination out/wgl
python Tests/Production/mesa_runtime.py probe --executable out/wgl/orbiter-wgl-probe.exe --output out/wgl-evidence
```

The [dedicated workflow](../../.github/workflows/production-bootstrap.yml)
executes Debug and Release on hosted Windows 2022. The MSVC-built probe creates a
visible Win32 window and a WGL 3.3 core context, compiles/links shaders, renders a
texture-backed FBO, checks all readback pixels, presents, resizes, deletes GPU
resources and closes the window/context. Three fresh context/window cycles must
pass. The wrapper requires llvmpipe, application-local Mesa DLLs and recorded
paths/SHA256 hashes of actual loaded DLLs; environment variables are not proof.

[Mesa UCRT64 lock](../../Tests/Production/mesa-ucrt64.lock.json) pins the full
20-package dependency closure (80 MB download). CI does not resolve rolling
packages. Runtime staging is local to the test executable and includes licenses;
no system OpenGL replacement occurs. Actual compiler, runner OS and CMake cache
are archived; a runner label alone is not a toolchain version lock. See the
[official Mesa deployment instructions](https://docs.mesa3d.org/drivers/llvmpipe.html)
and [official package metadata](https://packages.msys2.org/packages/mingw-w64-ucrt-x86_64-mesa).

If packaged Mesa cannot load, investigate the recorded dependency failure and
prepare a pinned Mesa/LLVM source build. If the hosted runner cannot create a
usable Windows window environment, the gate is blocked. Linux rendering,
compilation or an offscreen-only context cannot satisfy it.

## Production references and acceptance contracts

Before changing each production subsystem, capture repeatable original Windows
behavior with recorded tick inputs, fixed seeds, toolchain, source, assets,
binary hashes and callback ordering. Never automatically replace an accepted
reference. The original two-body reference remains separate and immutable.

Position/velocity/rotation/angular-velocity/MJD budgets remain respectively
0.01 m, 0.00001 m/s, 1e-8 rad, 1e-10 rad/s and 1e-10 days. Quaternion comparison
is sign independent. Mass/propellant budgets are 1e-8 relative with a 1e-8 kg
absolute floor. Contact/docking events must agree within one recorded physics
tick and 1 m / 0.1 m/s / 1e-3 rad. Validate budgets against repeated Windows runs
before extraction; a failure blocks advancement. Save/reload comparisons use
Windows round-trip results at the stock serialization precision.

Reference cases must cover Solar System ephemerides/orbits, main/RCS schedules,
autopilots, atmosphere/ground contact/docking, pause/warp, creation/deletion/focus,
vessel persistence/animations and callback order. No new numerical integrator or
generic-vessel fallback is permitted.

Scene evidence must identify engine object/class/module names, asset hashes,
mesh/group/material counts, camera transforms, visuals and animation state.
Windows OpenGL captures are the image reference: at 1280x720, landmark error
<=1 pixel and SSIM >=0.98 with only declared wall-clock/FPS masks. Instrument
semantics must match original source values at displayed precision. Also test
20 load/unload cycles and explicit missing/corrupt/ambiguous/incompatible failures.

Smoke-initialize the 157 unchanged scenarios. Interactive acceptance includes
DG Mk4 in orbit (all its objects), Virtual cockpit, DG-S ready for takeoff,
Docked at ISS, Atmospheric autopilot, DG to the moon tutorial and Atlantis ISS
Resupply. Reduced fixtures are engineering tools only.

Keep current Linux/Windows x64 Debug/Release regression CI and Windows application
tests. Inherited disabled Nightly and Artifact Cleanup workflows stay unchanged.
Validate the Intel/Mesa laptop on Wayland and X11/XWayland at 1920x1080 medium:
median frame <=33 ms and p95 <=50 ms in fixed exterior/cockpit runs. Software CI
is a correctness gate. Release data/kernel versions must be identical, verified
and licensed; missing coverage/assets must fail explicitly. Program/data files
are read-only, user settings/saves/logs/cache separate, independent of cwd.

Large packages/binaries belong in versioned release storage with hashes, not
repeated Git commits. Preserve accepted logs, traces, representative images,
reports and manifests beyond CI artifact expiry. Publish the native SDK/toolchain
compatibility policy and supported module list with the eventual release.
