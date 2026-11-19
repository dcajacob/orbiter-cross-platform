# Orbiter Launchpad for Qt

Browse the simulator's scenario folders, search by name, read scenario
descriptions, and launch the selected flight. The launcher restores the
selection when the simulator exits.

The original Orbiter banner and stock scenario help images are bundled in
the launcher. Screenshots appear in the description pane when the selected
scenario has them. A profile can also supply its own scenario help directory.

## Flight settings

Open **Flight settings… → Options** before launching a scenario. Choose
whether vessels consume fuel, set the glass-cockpit MFD size and update
interval, or change the 2D panel scale. **Save** updates
the active simulator configuration. Reopen the dialog to see the current
values, including settings changed in flight. Under **Visual effects**, choose
clouds, cloud shadows and planet night lights. Turning clouds off also hides
their shadows. Turning clouds back on restores the saved shadow preference.
**Maximum planet surface detail** sets a ceiling from 1 to 21. The detail
visible in a flight depends on camera distance and the installed planet tiles.

On native profiles, open **Flight settings… → Video** to set the flight window's
width and height in framebuffer pixels. Choose **Free** to edit them independently,
or choose **4:3**, **16:10**, or **16:9** to link them. Selecting a ratio adjusts
the height to fit the width. Editing either dimension then updates the other.
As in the Windows Launchpad, the saved width and height determine which ratio
appears when you reopen the page.
On a 2× Wayland display, choose even pixel dimensions so the compositor can
represent the requested framebuffer with a whole number of logical pixels.

On Linux, **Fullscreen on primary display** opens the flight at the display's
current resolution and refresh rate. Clear it to use your saved window size
again. **Vertical sync (VSync)** requests a swap interval of one when enabled
and zero when disabled, in either display mode. The driver or desktop
compositor can also pace presentation. Existing configurations use Orbiter's
`Fullscreen` and `NoVSync` keys. With both keys absent, flights open windowed
with VSync enabled.

The Linux OpenGL client leaves colour depth, graphics device selection,
device enumeration, stencil and page flipping to the renderer and driver.

Open **Flight settings… → Modules** to see the plug-ins installed for the
selected simulator. Check the ones you want and click **Save** before launching.
On Linux, **LuaMFD** adds the Lua Terminal MFD and **XRSound** enables spacecraft
audio when the profile includes its sound assets. LuaInline and LuaInterpreter
load automatically when a script needs them. Other native plug-ins are listed
with their availability. The Windows simulator uses its classic startup list.

Startup selections are saved in the active `Orbiter.cfg`. Native XRSound uses
the profile's `--xrsound-assets` launch option. Launchpad remembers its checkbox
per user and simulator configuration. Existing profiles with sound assets start
with audio enabled.

On Linux native profiles, open **Flight settings… → Extra** and choose a category.

| Category | Settings |
| --- | --- |
| Dynamic state propagators | Choose one to five stages, the Runge–Kutta or symplectic method per stage, time and angle targets, stage transition limits, and the maximum number of substeps. Angles are shown in degrees. |
| Orbit stabilisation | Enable Encke integration and set the perturbing-gravity and orbital step thresholds as percentages. |
| Cockpit displays (MFDs) | Choose automatic, exact, or power-of-two sizing for 2D displays, the threshold for switching from 256 to 512 pixels, and 256, 512 or 1024 pixels for virtual cockpit displays. |
| Planet atmospheres | Choose an installed atmosphere module per planet, use the installation default, or disable the module. Orbiter can still use atmospheric parameters supplied by the planet configuration. |
| Vessel graphics | Select standard or high-resolution Delta-glider and Atlantis textures and the Atlantis cockpit mesh when the corresponding stock assets are installed. |

**Save** applies the choices to subsequent flights using this configuration.
The atmosphere and vessel graphics overrides live in the profile's
`Orbiter.cfg`. **Installation default** uses the stock data selection. The
simulator resolves alternate assets in memory, so profiles can share an installation.

The classic perturbation subsampling and nonspherical suppression limits have
no consumers in the current flight dynamics. The native flight clock takes a
simulation tick interval on the command line. Classic fixed time per rendered
frame, Windows shutdown and logging options, GDI font controls, Direct3D
debug settings, and plug-ins with Win32 configuration dialogs are outside
this page.

### Coverage of the classic Windows launcher

| Classic page | Qt Launchpad |
| --- | --- |
| Scenarios | Scenario tree, search, descriptions and screenshots, launch and return. Native profiles also support start paused, saved flights, and copying a scenario. Classic quicksave management and contextual help are still missing. |
| Options | Fuel, cockpit instruments, clouds, cloud shadows, planet night lights and maximum surface detail, plus the Linux joystick setup wizard. |
| Modules | Installed plug-in list and startup selection. Native profiles identify automatic dependencies and unsupported plug-ins. Windows graphics clients are listed separately from selectable plug-ins. |
| Video | Native window width, height, and the three classic fixed aspect ratios. Linux also supports fullscreen at desktop resolution and a VSync toggle. |
| Extra | Linux native physics, orbit stabilisation, MFD resolution, installed atmosphere models and stock vessel graphics. |
| About | Open **About** in the main window for the selected simulator and Qt Launchpad build dates and versions, original component credits, Orbiter links, full credits and MIT license. The credits and license are bundled for offline use. Older installations without a build stamp show their simulator version as unavailable. |

Windows users can access the original pages through **Setup → Open classic
Launchpad**. [Classic page registration](../../Src/Orbiter/Launchpad.cpp)

## Build

Install Qt 6.4 or later with Qt Widgets, a C++17 compiler, and CMake. Build from
the repository root.

```sh
cmake -S Utils/Launchpad -B out/qt-launchpad -DCMAKE_BUILD_TYPE=Release
cmake --build out/qt-launchpad --config Release
```

On Linux, the joystick setup tool uses the same pinned GLFW as the simulator.
Install the Wayland and X11 development dependencies used by GLFW. For an
offline build, set `-DORBITER_GLFW_ARCHIVE=/path/to/glfw.tar.gz` to the
verified renderer dependency archive.

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

The optional native profile field `scenarioConfigs` maps individual scenario
paths to their own writable simulator configs. For example,
`"scenarioConfigs": {"Scenarios/Cloudy KSC tour.scn": "Flight settings/Cloudy KSC tour.cfg"}`.
Both paths resolve relative to the profile file. Selecting that flight uses its
config for Flight settings, joystick setup and launch. The XRSound switch is
shared across the profile.

The assets directory contains the stock `Scenarios` tree. The config file
holds the simulator and controller settings and should be writable so Orbiter
can save changes made in flight. Optional `keymap`, `environment` and
`unsetEnvironment` fields select a keymap and set or remove child-process
environment variables. For Linux audio, set `xrsoundAssets` to the directory
containing `XRSound/XRSound.cfg` and the stock `XRSound/Default` sounds.
In a source checkout this is `Sound/XRSound/assets`. The matching native
module build places `XRSound.so` in `NativeModules/Plugin`. Start in the
Delta-glider cockpit to hear propulsion sounds in orbit with the stock
SilenceOfSpace setting.

Linux can use the same simulator profile for stock and Apollo flights. The
optional NASSP installation adds vessel modules, MFDs and mission scenarios.
See the [NASSP build and installation instructions](../NASSP/README.md).

If `saves` is omitted, the launcher uses Qt's
per-user application data directory. **Ctrl+S** saves to `Quicksave.scn`,
which appears under **Saved scenarios** after you close the simulator.
**Start paused** is selected by default. Press **Space** to start time or
**Escape** to close the session.

### X11 software rendering

Mesa 26.0.8 llvmpipe can leave two allocations behind when Orbiter closes its
X11 renderer. The [private Mesa build](../../Tests/Production/GraphicsDriverLifetime/README.md)
releases the executable heap after the last generated function is freed.
Generate a separate profile for X11 software rendering, including Xvfb, with
Python 3.11 or later. Use the private Mesa build directory containing
`driver-build.json` and `install/`.

```sh
python3 -B Utils/Launchpad/make_x11_software_profile.py \
  --profile out/qt-launchpad/linux-profile.json \
  --mesa-build out/mesa-cleanup \
  --output out/qt-launchpad/linux-x11-software-profile.json
```

Select the generated file under **Setup → Open simulator profile**. It keeps
your scenario, configuration and saves paths and selects the checked Mesa
libraries for the simulator process. Use your regular profile for
hardware-accelerated sessions. The [Linux Phase 7 record](../../Docs/Production/LinuxPhase7Sparse.md)
includes the X11 Options and stock checks.

### Joystick setup

Open **Setup → Joystick setup…** and choose the connected controller. The
**Axes** and **Buttons** tabs show the same raw input numbering as the
simulator. Use **Detect…** and move the indicated control, or choose its
number manually. For throttle detection, start at idle and move toward
full power. **Reverse** lets you correct any axis direction.

The live hat indicator shows the direction even on the Axes tab. On the
**Buttons** tab, press a button or move a hat to bring its row into view.
Click the row's **Shortcut** to choose an Orbiter action, or choose a key
and optional Ctrl, Alt and Shift modifiers. The editor and button table show
what the shortcut does under the active Orbiter keymap, including common
Delta-glider and Atlantis controls. Other vessel and panel shortcuts depend
on the active vessel or display. **Unassigned** clears the binding.

In VelocityOne Flightstick PC mode, hold H1 in any of its eight directions
for a 45° quick look on each active axis in the cockpit or an external
tracking view. Releasing H1 restores your previous
angle. H2 pans continuously, and pressing it straight in centers the cockpit
view. Each control can be turned off in the wizard. An explicit H2 click
assignment takes priority over recentering.
An H1 direction with an explicit shortcut or roll-to-yaw assignment uses
that binding.

**Save** uses the mapping on the next native Linux flight. It stores the
active controller and bindings alongside the simulator configuration.
**Use simulator defaults** restores the joystick settings from that
configuration. The custom throttle waits for deliberate movement after
connection or reconnection.

The VelocityOne Flightstick's red touchpad click is listed separately in PC
mode. If it shows **Needs access**, install the included Linux device rule,
reload the rules, and unplug and reconnect the stick.

```sh
sudo install -m 644 Utils/Launchpad/69-orbiter-velocityone-touchpad.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
```

With a shortcut assigned, the touchpad acts as an Orbiter button while the
flight window has focus. It acts as a pointer again when you leave the window.

### Copy and edit a scenario

Select a stock scenario and click **Copy and edit…**. Give the copy a name,
set its start date in UTC, and optionally move one vessel. Landed vessels take
longitude, latitude and heading. Orbiting vessels with Cartesian state take
position and velocity in Orbiter's ecliptic axes relative to the current
reference body.

The copy is selected under **Saved scenarios**. Click **Launch Orbiter** to
fly it, press **Ctrl+S** to quicksave, and press **F5** to reload the quicksave.
The editor preserves the stock file, vessel class and module settings. It
leaves docked and attached vessels and orbits defined by orbital elements in
place. Recorded flights are excluded because playback supplies their starting
state.

### Edit a paused Linux flight

Press **F7** in the simulator to open the scenario editor. If time is
running, click **Pause to edit**. Enter a name and choose **Shuttle PB** or
**Delta-glider** to add it near the focused vessel.

Select a vessel and click **Move vessel** after entering its new coordinates.
In orbit, enter position in meters relative to the displayed body, using
Orbiter's ecliptic axes. On the ground, enter longitude, latitude and heading
in degrees. **Remove vessel** asks for confirmation. Use a standalone vessel
and switch focus to another vessel before removing the focused one.

Close the editor, press **Ctrl+S** to quicksave, and press **F5** to reload.

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
