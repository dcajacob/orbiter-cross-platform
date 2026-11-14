# Runway 33 Vulkan client

This opt-in client opens the supplied Runway 33 scenario in Orbiter and draws the
stock DG-S exterior with its original textures and initial external camera. The
client uses SDL3's Vulkan backend and a shared pair of SPIR-V shaders. A neutral
background and simple sunlight keep this milestone focused on the spacecraft.

Build with CMake 3.24 or newer, a matching Orbiter build, SDL3 3.4 or newer, and
`glslangValidator` from the Vulkan SDK or your package manager. The shaders
are embedded in the module. For an offline build, use
`ORBITER_VULKAN_PREBUILT_SHADERS` to supply matching `Ship.vert.spv` and
`Ship.frag.spv` compiled from the files in `shaders/` with `glslangValidator -V`.

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

Use the usual stock assets, ephemeris data, and planetary archive paths. Set
`WindowWidth = 1280` and `WindowHeight = 720` in the configuration you pass to
Orbiter. The optional evidence directory receives the first rendered Vulkan
frame as `vulkan-frame.bmp`.

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
containing `Orbitersdk/include` and `Orbitersdk/lib`, and to the Dear ImGui
headers used by that same Orbiter build. Set `SDL3_DIR` to the CMake package
directory if CMake needs help finding the SDL3 SDK.

```powershell
cmake -S OVP/VulkanClient -B C:/vulkan-build -G Ninja -DCMAKE_BUILD_TYPE=Release `
  -DORBITER_TEST_RUNTIME=C:/orbiter-build `
  -DORBITER_IMGUI_SOURCE=C:/dependencies/imgui
cmake --build C:/vulkan-build
```

Place `VulkanClient.dll` in `Modules/Plugin` and the x64 `SDL3.dll` beside
`Orbiter.exe` in a Windows Orbiter runtime with the stock assets. Copy the supplied
`Runway33.scn` to `Scenarios`. Select `VulkanClient` as the sole graphics
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
