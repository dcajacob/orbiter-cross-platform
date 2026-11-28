# Orbiter Project Launcher

Choose a **Runtime** in the Qt Launchpad, select a scenario, and click **Launch Orbiter**. The project and bundled applications use the same scenario browser, flight settings and launch code. Closing the simulator returns you to the browser.

The dropdown shows one entry per installed host family: **OpenGL**, **Vulkan**, **D3D9**, and **Classic Windows** on Windows. Native profiles without a graphics field use the legacy OpenGL command line. Add-ons installed into an active runtime contribute scenarios and modules to that runtime. Separate mission bundles and fixed-flight shortcuts have their own launch entries outside this catalogue.

Discovery checks registered locations, standard installation directories, established checkout output directories and `ORBITER_RUNTIME_PATH` (a list separated by the platform path separator). An installation needs a scenario-capable simulator and a profile pointing to its assets, data, modules, planets and config. The supported directory layouts use `Launchpad profile.json`, `linux-profile.json`, `orbiter-profile.json`, `vulkan.json` or `d3d9.json`. Classic Windows installations can also be discovered from `Orbiter.exe`. A bare renderer or vessel module is insufficient.

**Setup → Add runtime folder…** registers an installation or its parent directory. **Open simulator profile…** selects a specific profile, including a different installation of the same family. The runtime control's tooltip shows the active path. **Refresh runtimes** rescans after installation. **Manage search locations…** removes registered folders or profiles. The project application remembers its selection separately from the bundled Launchpad. Launching a bundle with an explicit profile starts in that installation.

## Build

Use the [Qt Launchpad build dependencies](../Launchpad/README.md#build). The regression test also requires Qt Test.

```sh
cmake -S Utils/ProjectLauncher -B build/project-launcher -DCMAKE_BUILD_TYPE=Release
cmake --build build/project-launcher
ctest --test-dir build/project-launcher --output-on-failure
cmake --install build/project-launcher --prefix "$HOME/.local"
```

On Linux choose **Orbiter Project Launcher** from the application menu. The binary directory must be on the desktop session's executable search path. Use `orbiter-project-launcher --list` to print the active family profiles, `--search <location>` for a session search location, or `--add-location <location>` to register one.
