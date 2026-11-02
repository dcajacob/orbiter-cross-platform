# Production native Orbiter release

The native stock release is **not complete**. `orbiter-native` is a portability
POC using the restricted `SimulationSession` and procedural geometry. Its
[accepted evidence](../../Tests/Portable/ClientVerification/README.md) remains
valid for that scope. It does not count as production engine/client integration.

The [native production external view](NativeExternalView.md) now runs actual
Sol, ISS and source-built ShuttlePB with the shared OpenGL renderer on the laptop.
Its local state/camera/landmark checks and full-image SSIM pass the frozen Windows
budgets. The [native orbital flight host](NativeFlight.md) adds keyboard/joystick
control paths, independent timing and original docking/persistence. These remain
narrower deliveries than the stock release.

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

[The donor inventory](../../Tests/Production/renderer-donor.lock.json) pins file
hashes and the SOIL2/NanoVG/libnsbmp gitlink commits separately. Those dependencies
are not contained in a parent Git archive; their source/license audits remain
required before import. The old ImGui/OpenGL backend also needs adaptation to
the current production ImGui API.

Linux x86-64, Ubuntu 24.04 minimum, stock modules rebuilt from source with the
same native SDK/toolchain, and SPICE with matching kernels define the release.
Unmodified Windows DLLs, proprietary hardware integrations, Windows auxiliary
tools and full D3D9 visual parity are deferred. No Wine or visual proxy objects
may satisfy a production acceptance case.

## Capability and dependency inventory

| Capability | Current native implementation | Release requirement / dependency |
| --- | --- | --- |
| Vecmat, elements, two-body RK4 | Verified restricted fixtures | Preserve frozen references unchanged |
| Native window and input | Production orbital flight host with camera, keyboard and raw joystick control paths; controller hardware acceptance pending. Procedural viewer remains a separate POC | Native production window, flight input and real graphics client |
| Production world and session | Shared frame ordering and actual celestial `PlanetarySystem`, `Body`/`RigidBody`/`CelestialBody`/`Star`/`Planet`/`Base`/`VesselBase`; actual native Vessel/Camera/Session external view added; general application integration pending | Existing lifecycle, shared engine library and platform services |
| SPICE Solar System | Actual native celestial modules; hosted Windows/Linux Debug/Release direct-callback parity passes, actual native Sol world/external-view integration added | Current `Src/Celbody/SPICE`, CSPICE, `orbiter.bsp`, TLS/PCK and coverage verification |
| Native module ABI | Internal loader/bootstrap and actual celestial/atmosphere APIs with SDK-build and toolchain checks; checked source-built ShuttlePB/native vessel SDK added | Source-built vessels, celbodies, atmospheres, plugins; version/toolchain check |
| Real stock meshes/materials/animations | Production CPU `Mesh`/`MeshManager`; actual stock external meshes/materials/animations integrated for ISS/PB | Existing CPU mesh data separated from D3D resources; actual group identities |
| Planet tiles and elevation | Shared archive reader and actual elevation manager; frozen Windows/Linux direct-query parity passes; native planet/base component verification added | Portable fixed-width archives, 64-bit offsets; engine contact queries independent of visibility |
| Resource resolution | Indexed resolver integrated with native production configuration/meshes/textures | Indexed Windows-separator/case-insensitive resolver with ambiguous alias errors |
| Texture loading | Shared real OpenGL decoder exercised with stock external assets | Signature-based DDS DXT1/3/5 and uncompressed formats; BMP in `.dds` files |
| Propulsion, RCS, atmosphere, docking, contacts | Original native Vessel and atmosphere; component RCS/autopilot and rendered orbit states pass; interactive flight/contact cases pending | Preserve original systems; production references before extraction |
| HUD/MFD/2D panels/VC/Sketchpad | Unsupported | Original instruments, redraws, surfaces, fonts/TextW, picking and interaction |
| Lua, tutorials, playback, editor, audio | Unsupported | Bundled modules/scripts and portable views over existing logic |
| Installation and assets | Source-built production preview with explicit verified stock-data roots; POC bundle remains separate | Relocatable runtime, native SDK, verified/offline/resumable separate asset installer |

[Graphics callback inventory](graphics-capabilities.csv) and
[Sketchpad method inventory](sketchpad-capabilities.csv) explicitly record
native delivery status and the original donor defects. The inherited fatal surface,
material and TextW implementations were repaired for the real Windows client;
the shared renderer now also runs natively. Current native coverage is the narrow
external view. Instrumentation, panel/VC redraws, advanced Sketchpad calls and
full stock call coverage still require their own gates. Silent no-op success is
not an implementation. The donor SDK/core/math changes are excluded.
[Windows evidence](WindowsClient.md) and [native evidence](NativeExternalView.md)
record their separate tested scopes.

Other dependencies: DirectX June 2010 and Windows SDK/MSVC for preserved Windows
builds; Lua and LuaFileSystem/Penlight; atmosphere modules; miniaudio/XRSound;
mesh/texture/gravity data; renderer dependencies including GLAD, SOIL2, NanoVG,
libnsbmp and fonts. License closure must accompany selective renderer import.
Core MIT and D3D9 LGPL components retain their existing licenses. The pinned Mesa
runtime lock lists package licenses and staging preserves the distributed license
files. The [dependency lock](../../Tests/Production/dependencies.lock.json) and
[input notices](../../Tests/Production/Licenses/INPUTS.md) record the current
source/runtime/data terms. The audited versioned input bundle excludes the
publication-restricted Architext font; its default UI dependency must be resolved
before the installed release. No new SPDX license is asserted for the historical
NRLMSISE C package; its author notice is retained.

## Ordered delivery gates

| Phase | Delivery | Status / exit condition |
| --- | --- | --- |
| 0 | Honest POC labeling, scope and inventories | Source inventory implemented; no production runtime claim |
| 1 | Production Windows references and hosted WGL | Accepted: original orbit/propulsion, 14 repeated behavior cases, Debug/Release comparison, hosted WGL and data/resource locks |
| 2 | Real Windows OpenGL client | Hosted Debug/Release execution passed; actual Sol/ISS/ShuttlePB, deterministic images/states, normal teardown. [Evidence and commands](WindowsClient.md) |
| 3 | Production engine/platform boundary | Native shared production world, original Vessel/Camera/Session and checked source-built modules now build and run. General application, instrumentation and module coverage remain in progress. [Scope and remaining gates](EngineBoundary.md) |
| 4 | Native real world/external client | Narrow Sol/ISS/ShuttlePB external view runs on laptop Wayland and hosted Ubuntu 24.04 Debug/Release. Current Windows application/client and frozen state/image/landmark checks pass. General compatibility, repeated in-process sessions and remaining hardware gates are still open. [Evidence](NativeExternalView.md) |
| 5 | Usable flight and interaction | Orbital ShuttlePB flight, docking, persistence and native keyboard checks pass. Atmosphere, control surfaces and resting/contact cases pass. An actual upright takeoff/landing is runnable, but controlled-flight mass/propellant parity and uncontrolled-impact attitude parity fail their unchanged limits. Phase 5 remains open. [Orbital evidence](NativeFlight.md), [ground-flight status](GroundFlight.md) |
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

[Accepted hosted WGL evidence](../../Tests/Production/Verification/README.md) records
actual Debug/Release execution, driver paths/hashes and preserved raw artifacts.

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

## Production Windows references

The test-only `ProductionReferenceDriver` is built with
`ORBITER_PRODUCTION_REFERENCE_CAPTURE=ON` in the existing Windows application.
It requires actual stock ISS/ShuttlePB objects and a source-built ShuttlePB
module, observes Sun/Earth/Moon/ISS/PB, and optionally commands main engine,
linear RCS and pitch RCS on declared ticks. It records original module pre/post notifications and controls. The separate
`ProductionBehaviorDriver` now observes real vessel callback boundaries and
finalized application states; it does not replace production implementations.

`capture_reference.py` requires all production implementation/dependency files
under `Src`, `Orbitersdk`, `Extern` and root CMake to match the frozen revision.
Only the test driver/build wiring is added. Each orbit and controlled case runs
twice for 6,000 recorded seconds. The driver observes finalized S0 at the start of
PreStep, before control application; PostStep precedes finalization and is never
sampled. A 6,001st application frame permits observation of finalized tick 6,000.
The existing finalization observer also records the PB quaternion trace. No
propagation formula, world update or public SDK change is needed.

`trace.csv` retains the existing primary-relative vessel trace contract. In
`production-state.csv`, positions/velocities use Orbiter's global ecliptic axes
in m and m/s; rotation matrices map local axes into those global axes. Mass/fuel
are kg. `wx/wy/wz` are body-frame rad/s for ISS/PB; fuel and ground contact also
apply only to vessels. Those slots are inapplicable zeros in celestial-body rows,
not measurements of a planet's spin. The report declares this field coverage.
MJD and simulation seconds follow the original application clock. Matrix rows
are orthonormality-checked, and vessel rotation comparisons are sign independent.

The separate official [stock data lock](../../Tests/Production/stock-data.lock.json)
pins the matching upstream release package by GitHub's published SHA256 and
463 extracted file hashes. `prepare_data.py` stages only data, never release
binaries/modules/configuration over the source build. Offline verification is
available with `--verify-only`. This test provisioner is not the final resumable
asset installer. The upstream `latest` asset URL can disappear or be replaced;
a different hash fails explicitly. The audited versioned mirror described below
preserves these consumed data bytes and excludes the restricted Architext font.
The final asset installer and packaged font policy remain later release work.

Candidate output directories must not exist before capture. Initial orbit and
propulsion references are now [explicitly accepted and frozen](../../Tests/Production/Reference/README.md)
from hosted source `e70041fa`: repeats are byte-identical, Debug/Release errors are
zero and independent fuel accounting passes. Normal CI verifies the current
application against that evidence using `--reference`; no script writes or
refreshes an accepted reference automatically. These initial references did not
load the atmosphere modules at their install locations and do not validate
atmospheric behavior. The separately frozen fourteen-case behavior suite below
loads those source-built modules explicitly and completes the remaining Phase 1
coverage, including contact/docking, autopilot, clocks, lifetime and persistence.

[The final verification run](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41189526342)
passes this immutable-reference path in both Windows configurations. Current
trace, state, event and identity files are byte-identical to the accepted evidence.
The portable Linux/Windows matrix and native SPICE data audit pass on the same
tested code. Preserved reports distinguish accepted capture from later verification.

### Independent SPICE data coverage

```sh
cmake -S Tests/Production/SpiceAudit -B out/spice-audit -DCMAKE_BUILD_TYPE=Release
cmake --build out/spice-audit
python3 -B Tests/Production/audit_spice.py \
  --executable out/spice-audit/orbiter-spice-data-audit --data /path/to/verified-data \
  --default-mjd 61344.5 --report out/spice-audit/coverage.json
```

This native audit links the existing pinned CSPICE library and directly queries
all 41 stock Sol bodies plus their barycentres at the distinct stock scenario
epochs. It validates the actual TLS/PCK/BSP hashes and requires an invalid epoch
to produce a clear coverage failure. The query output is SI metres and m/s in
ECLIPJ2000 axes. It does not run Orbiter's world, interpolation or graphics and
cannot replace production references. The separate data CI uses Ubuntu 24.04.

Seven unchanged scenarios have no valid numeric Date field and therefore default
to the wall clock in production `State::Read`: the three lunar-transfer/entry
challenges, both Today scenarios and the two Earth-Moon/Jovian ephemerides views.
The audit records them and uses the explicitly supplied coverage epoch, without
editing the files. A production replay of these scenarios must record/control
the application's default clock before world creation. Local GCC 15.2/CSPICE
N0067 passes 11,481 queries across 129 epochs, including MJD 61344.5, and the
out-of-coverage negative case. [Hosted Ubuntu 24.04/GCC 13.3](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41187217756)
passes the same audit, with byte-identical query output. Original evidence and
the separate local report are preserved in `Tests/Production/Verification`.

### Standard planet data, separate from SPICE

The pinned nightly release ZIP contains no Earth tile tree. Its orbital fixture
references must not be treated as terrain or graphical acceptance. The publisher's
[Orbiter 2016 core ZIP](https://www.orbiter-forum.com/resources/orbiter-2016-core-zip-edition.5425/)
contains the standard planet archives, which the current source supports. The
separate `standard-planets.lock.json` pins the publisher archive and 28 `.tree`
file hashes, including Earth/Moon/Mars surface and elevation and Earth clouds.
Only planet archive data is selected; the production SPICE model/kernels and
source-built modules/configuration remain authoritative.

An existing compatible directory was verified locally without modification:

```sh
python3 -B Tests/Production/prepare_data.py \
  --lock Tests/Production/standard-planets.lock.json \
  --destination /path/to/existing/Orbiter-2024 --verify-only
```

For an isolated extraction, supply the verified publisher ZIP with `--archive`
and a separate `--destination`. These planet archives were not part of the frozen
orbit fixture's input profile. Further production terrain/scene references must
record the combined profile explicitly. Durable package storage, complete license
review and the final resumable asset installer remain outstanding.

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

## Accepted behavioral references and the real-client gate

Phase 1 is accepted from [hosted run 41193020450](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41193020450).
[Fourteen behavioral references](../../Tests/Production/BehaviorReference/README.md)
cover all RCS groups, original autopilots, atmosphere, real terrain/contact,
docking/attachments, clock controls, vessel lifetime/focus, DG-S animation and
stock save/reload. Every run repeats identically within its build. Debug/Release
state comparisons pass without tolerance changes. Actual automatic docking to
ISS occurs at tick 250. Saved states are observed only after finalization.

The original two-body and production orbit/propulsion goldens remain untouched.
`observation_source.py` first verifies that the accepted observation source
conserves every original production byte after removing its marked test blocks.
During Phase 3 it also audits the explicit extraction ledger and the verbatim SDK
value-record moves. Frozen runtime comparisons remain a separate required gate.
Internal observation exports are compiled only by the test option; Windows SDK
declarations and binary layouts are preserved.

```sh
python3 -B Tests/Production/observation_source.py
python3 -B Tests/Production/frozen_reference.py
python3 -B Tests/Production/frozen_behavior.py
```

[Versioned audited inputs](https://github.com/dcajacob/orbiter-cross-platform/releases/tag/production-inputs-v2)
retain original data bytes, notices and hashes outside Git. The 2016 ZIP parts
reconstruct the intact original archive. Current stock data is a filtered bundle
with the restricted font excluded, not a mirror of the complete executable ZIP.
The [storage lock](../../Tests/Production/input-storage.lock.json) identifies the
actual published assets. Original frozen input-profile hashes remain unchanged.

The real separately built Windows `GraphicsClient` now executes with Win32/WGL
and actual Sol, ISS and ShuttlePB objects, meshes, materials, textures and
camera/visual callbacks. [The client milestone](WindowsClient.md) records the
passing scope, reproducible commands and remaining gates. [Production engine
extraction](EngineBoundary.md) is in progress: the actual `Body`, `RigidBody`,
propagators, celestial-body/star calculations, CPU mesh objects and planetary
archive reader build in a shared Windows/Linux library.
The [actual celestial world](../../Tests/Production/World/README.md) now loads
Sol and advances its original finalized states in the shared core. Native
vessels, their SDK, the camera and full session/client integration still need
extraction; the restricted POC session remains regression coverage.
