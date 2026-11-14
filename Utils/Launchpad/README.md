# Orbiter Launchpad for Qt

Browse the simulator's scenario folders, search by name, read scenario
descriptions, and launch the selected flight. The launcher restores the
selection when the simulator exits.

## Build

Install Qt 6.4 or later with Qt Widgets, a C++17 compiler, and CMake. Build from
the repository root.

```sh
cmake -S Utils/Launchpad -B out/qt-launchpad -DCMAKE_BUILD_TYPE=Release
cmake --build out/qt-launchpad --config Release
```

For a Qt installation outside the system search path, pass
`-DCMAKE_PREFIX_PATH=/path/to/Qt/6.x/platform` at configure time. Use the
native Qt kit for the target architecture. When distributing the launcher,
deploy the matching Qt libraries and platform plugin alongside it.

## Linux

Open a native simulator profile using **Setup → Open simulator profile**, or
start `orbiter-launchpad --profile /path/to/profile.json`. A profile points to
an existing cockpit-capable native build plus its matching resources. Relative
paths are resolved against the profile file.

```json
{
  "mode": "native",
  "executable": "engine/orbiter-production",
  "assets": "resources",
  "data": "celestial-data",
  "modules": "engine/NativeModules",
  "planets": "planet-archives",
  "config": "Orbiter.cfg",
  "saves": "user/Scenarios",
  "help": "Html/Scenarios"
}
```

The assets directory contains the stock `Scenarios` tree. The config file
holds the simulator and controller settings and should be writable so Orbiter
can save changes made in flight. Optional `keymap`, `environment` and
`unsetEnvironment` fields select a keymap and set or remove child-process
environment variables. If `saves` is omitted, the launcher uses Qt's
per-user application data directory. **Ctrl+S** saves to `Quicksave.scn`,
which appears under **Saved scenarios** after you close the simulator.
**Start paused** is selected by default. Press **Space** to start time or
**Escape** to close the session.

## Windows

Place the launcher next to an installed `Orbiter.exe`, or choose it through
**Setup → Choose Orbiter.exe**. The launcher uses the installation's
`ScenarioDir` from `Orbiter.cfg` when present. It launches the existing
executable from its installation directory with `--scenariox`, which returns
control to Qt when Orbiter exits. Windows startup and graphics settings come
from the existing installation. **Setup → Open classic Launchpad** opens
`Orbiter.exe` with its original startup screen.

## macOS

The CMake target is configured as a macOS app bundle for native Qt kits.
Launching a stock scenario requires a production macOS simulator. The portable Mac test
viewer supports its own limited flight fixture and does not run stock missions.
