# Optional NASSP modules on Linux

The Qt Launchpad can open stock and Apollo scenarios from one library using the same `orbiter-production` executable. Orbiter reads the vessel class and solar system from the scenario. For example, the Apollo 11 lunar-orbit save loads the `ProjectApollo/Saturn5` and `ProjectApollo/LEM` vessels and the Earth VSOP87 and Moon ELP82 ephemerides. Stock `Sol` scenarios keep their original integrator behavior and SPICE ephemerides.

## Build matching modules

Start with a native Release build of Orbiter with cockpit, native vessels, Lua, celestial modules, and the matching OpenGL client. Build the optional components against that engine's generated SDK. Use the same compiler, build configuration, and Orbiter checkout for all of them. For the Linux NASSP 9 content snapshot used here the add-on source is `dcajacob/NASSP` at `5bef1ba3e842c8de3d9a3b5a97c26a71b36f3c59`.

```bash
cmake -S Src/Celbody/NativeEphemeris -B "$build/ephemeris" \
  -DCMAKE_BUILD_TYPE=Release -DORBITER_ENGINE_BUILD="$engine"
cmake --build "$build/ephemeris"
cmake -S "$nassp/Orbitersdk/samples/ProjectApollo" -B "$build/nassp" \
  -DCMAKE_BUILD_TYPE=Release -DNASSP_BUILD_NATIVE_LINUX=ON \
  -DORBITER_NATIVE_SOURCE_DIR="$PWD" -DORBITER_NATIVE_BUILD_DIR="$engine"
cmake --build "$build/nassp"
```

Here `$engine` is the absolute Orbiter build directory, `$build` is a separate build directory, and `$nassp` is the NASSP source checkout. The original data bundle also includes Stage and VesselBuilder1 vehicles for other missions. Build the Linux ports of Stage2010 and VesselBuilder1 using their own CMake projects and the same `ORBITER_NATIVE_SOURCE_DIR` and `ORBITER_NATIVE_BUILD_DIR` arguments. The native loader checks the SDK identity, architecture, module kind and C++ ABI when loading a plug-in.

## Add the mission library

Run the staging tool from the Orbiter checkout with a new destination. `$apollo_package` points to an extracted native Linux player bundle supplying the mission data and notices. The two auxiliary build directories supply `stage.so` and `VesselBuilder1.so`.

```bash
python3 Utils/NASSP/stage_linux.py \
  --engine "$engine" --stock-assets "$stock_assets" --stock-data "$stock_data" \
  --stock-sound Sound/XRSound/assets --apollo-package "$apollo_package" \
  --nassp-build "$build/nassp" --stage-build "$build/Stage2010" \
  --vesselbuilder-build "$build/VesselBuilder1" --destination "$content"
```

In the normal native Launchpad profile point `executable` to the shared engine, `assets` and `xrsoundAssets` to `$content/resources`, `data` to `$content/celestial-data`, and `modules` to `$content/NativeModules`. Keep the installed planet archives, keymap, save directory and saved flight settings. In **Modules**, enable **ApolloRTCCMFD** and **ProjectApolloMFD** to use the Apollo instruments. The source bundle's immutable qualification record is copied as `apollo-input-build.json` and describes the input bundle only.

Select **Apollo 11 - Native Linux Saves → 04 - Lunar orbit** to fly Columbia docked with Eagle. The same Launchpad lists the stock scenarios and your personal saves. A stock-only installation can continue using its usual stock module and data paths with the same executable.

## Linux flight check

On November 18, 2026, Dan confirmed the Apollo 11 lunar-orbit time-acceleration check passed on his desktop. The tested Ubuntu 26.04.1 x86-64 executable had SHA-256 `c2067cfb44724de3c7af7271f87479841474bae334178963222dacdc5e6cacab`.

On the same build, a muted Qt Launchpad check advanced 30 simulated minutes at 100×, returned to 1×, paused, saved and resumed. A separate process reloaded the save with both docking links intact. The cloudy KSC tour and Florida night-orbit frames matched their saved references pixel for pixel. These were focused checks of the shared Linux simulator.
