# Runway 33 Vulkan client

This opt-in client draws the focused vessel's exterior on Windows and Linux
using SDL3's Vulkan backend and shared SPIR-V shaders. `Runway33.scn` starts
the stock DG-S at Kennedy. `ShuttleA-Runway33.scn` places an unloaded stock
Shuttle-A at the same position, heading, and scenario time for comparison.

Both vessels use the same mesh slots, group visibility, texture lookup, and
Orbiter ambient, diffuse, emissive, and specular material properties. Mesh
animations run in each slot's local coordinates before applying its vessel
offset. The ground shadow follows that same geometry.

The client streams stock Earth surface tiles from `Earth/Archive/Surf.tree` and
uses Orbiter's elevation data. It keeps detailed tiles around the vessel and
extends coarser terrain toward the horizon with distance haze. During flight
it stages tiles over several frames and replaces each coarser tile when all
four of its children are ready.

## Earth base scenery

The Vulkan client discovers bases from Orbiter's Earth base list. It uploads
each base's textured surface tiles, pavement, landing pads, runways, and
above-ground structures when the camera comes within 100 km. The client keeps
all nearby bases resident and releases each after 110 km. Stock and add-on bases
use the same Orbiter mesh and texture interfaces. Surface tiles and pavement
are drawn before ground shadows. Each base with shadow casters has its own
sunlight depth map. `EnableShadows = FALSE` disables building shadows.

`Kennedy-Pads.scn` and `Habana-Pads.scn` show the DG-S beside the stock pads
in daylight. Both start in exterior view and can be inspected while paused.
The stock **DG at Edwards AFB** scenario also exercises overlapping ranges for
Edwards, Mojave, Palmdale, China Lake, and Inyokern. `VAB-LowPass.scn` starts
the DG-S airborne beside Kennedy's Vehicle Assembly Building.

For matched flyby frames, start the scenario unpaused with a 0.05-second
simulation step. Set `ORBITER_VULKAN_CAPTURE_DIR` to an existing output
directory to save BMPs at 0.1-second simulation intervals. Use a fresh directory
for each recording. Leave the variable unset for frame-time measurements.

## DG-S takeoff

1. Press **Ctrl+P** to resume.
2. Hold **Ctrl+Numpad +** until the title bar shows **Main 100%**. Release the keys
   to keep the selected throttle.
3. At roughly **135 m/s**, hold **Numpad 2** to rotate. Release it once the DG-S
   is climbing, around **10–15 m AGL** in the supplied scenario.
4. Use **Numpad 8** to lower the nose, **Numpad 4/6** to bank, **Numpad 1/3** to yaw,
   and **Numpad \*** to kill main thrust. Right-drag or use **Ctrl+arrow keys**
   to orbit the external camera. Scroll to change camera distance.

The current scope is the external focus vessel and regional Earth terrain.

## Optional Kennedy imagery

The offline imagery pack covers the Shuttle Landing Facility runway, Launch
Complex 39A, and Launch Complex 39B. It uses public 2023 Florida NAIP imagery
from [USDA Forest Service GTAC / GeoPlatform IIPP](https://imagery.geoplatform.gov/iipp/rest/services/NAIP/NAIP_plus/ImageServer).
The 1536-pixel detail tiles sample approximately 0.35 m east–west and 0.40 m
north–south near Kennedy. Mipmaps and coarser tiles are included. The imagery
feathers into stock Earth textures at the edges of the coverage.

Extract the pack and set `ORBITER_VULKAN_KENNEDY_IMAGERY` to the directory
containing `imagery.json` and the numbered tile directories before starting
Orbiter. The Vulkan client reads the tiles from disk. With the variable unset,
the client uses the stock Earth surface archive.

On Linux:

```sh
export ORBITER_VULKAN_KENNEDY_IMAGERY=/path/to/Orbiter-Kennedy-NAIP-2023
```

In Windows PowerShell:

```powershell
$env:ORBITER_VULKAN_KENNEDY_IMAGERY = 'C:\path\to\Orbiter-Kennedy-NAIP-2023'
```

To build the pack yourself, install NumPy, Requests, and Pillow with BC1 DDS
encoding support, then run:

```sh
python3 OVP/VulkanClient/PrepareKennedyImagery.py \
  /path/to/Textures/Earth/Archive/Surf.tree /path/to/Orbiter-Kennedy-NAIP-2023
```

## Repeatable runway circuit

Copy `VulkanCircuit.lua` into the isolated Orbiter runtime's `Script` directory
and add `Script VulkanCircuit` inside `BEGIN_ENVIRONMENT` in a copy of
`Runway33.scn`. Run that scenario unpaused. The Lua controller uses the stock
DG-S controls to fly a left circuit, land on Runway 33, brake, and pause.
It writes `vulkan-circuit.csv` in the working directory. Use a 0.05-second
simulation step for repeatability (`--fixed-step 0.05` on Linux,
`--fixedstep=0.05` on Windows).

Set `ORBITER_VULKAN_FRAME_TRACE` to a writable CSV path to record intervals
between Vulkan frames, CPU-side scene and terrain times, tile staging, and
aircraft pose uploads, initial base upload time, and shadow map refreshes.

Build with CMake 3.24 or newer, a matching Orbiter build, SDL3 3.4 or newer, and
`glslangValidator` from the Vulkan SDK or your package manager. The shaders
are embedded in the module. For an offline build, use
`ORBITER_VULKAN_PREBUILT_SHADERS` to supply the SPIR-V files for all vertex and fragment sources
in `shaders/`. Compile each with `glslangValidator -V` and name the output
after the source with a `.spv` suffix.

## Linux

Build the production engine with the stock native vessel, celestial, and cockpit
options enabled. Build this module separately against that engine's generated SDK
with the same build configuration.

```sh
cmake -S OVP/VulkanClient -B /path/to/vulkan-build -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DORBITER_ENGINE_BUILD=/path/to/native-engine-build
cmake --build /path/to/vulkan-build
cp /path/to/vulkan-build/VulkanClient.so \
  /path/to/native-engine-build/NativeModules/Graphics/
```

Use the stock assets, ephemeris data, and planetary archives (Earth surface and
elevation). Set `WindowWidth = 1280` and `WindowHeight = 720` in the configuration
you pass to Orbiter. The optional evidence directory receives a Vulkan frame
as `vulkan-frame.bmp`. Add `--capture-time <sim-seconds>` to capture during flight.

```sh
/path/to/native-engine-build/orbiter-production \
  --graphics vulkan \
  --assets /path/to/stock-assets --data /path/to/ephemeris \
  --modules /path/to/native-engine-build/NativeModules \
  --planets /path/to/planetary-archives --config /path/to/Orbiter.cfg \
  --scenario OVP/VulkanClient/Runway33.scn \
  --frames 120 --evidence /path/to/evidence
```

Omit `--frames` to keep the window open for inspection. The default graphics
selection remains OpenGL.

## Windows

Use an x64 MSVC developer prompt. Point the build to the Orbiter build directory
containing `Orbitersdk/include`, `Orbitersdk/lib`, and
`Src/Orbiter/Production/orbiter_production_boundary.lib`. Point
`ORBITER_IMGUI_SOURCE` to the Dear ImGui headers used by that same build. If the
client sources are staged separately, set `ORBITER_VULKAN_SOURCE_ROOT` to the
matching Orbiter source checkout. Set `SDL3_DIR` to the CMake package
directory if CMake needs help finding the SDL3 SDK.

```powershell
cmake -S OVP/VulkanClient -B C:/vulkan-build -G Ninja -DCMAKE_BUILD_TYPE=Release `
  -DORBITER_TEST_RUNTIME=C:/orbiter-build `
  -DORBITER_IMGUI_SOURCE=C:/dependencies/imgui
cmake --build C:/vulkan-build
```

Place `VulkanClient.dll` in `Modules/Plugin` and the x64 `SDL3.dll` beside
`Orbiter.exe` in a Windows Orbiter runtime with the stock assets. Copy the supplied
`.scn` files to `Scenarios`. Select `VulkanClient` as the sole graphics
client in that runtime. For the reference capture, use these settings and set
`PlanetTexDir` to the stock Earth archive directory's parent, `Textures`.

```ini
StartPaused = TRUE
EnableParticleStreams = FALSE
InfobarMode = 1
MenubarMode = 1
WindowWidth = 1280
WindowHeight = 720
ACTIVE_MODULES
  VulkanClient
END_MODULES
```

From that runtime directory, run:

```powershell
.\Orbiter.exe --scenario=Runway33
```

Use `--scenario=ShuttleA-Runway33` for the Shuttle-A view. For a Windows
reference capture, set `ORBITER_VULKAN_CAPTURE_FRAME` to a writable BMP path.
The client saves the first rendered vessel frame directly from Vulkan.
