# Native graphical client milestone

`orbiter-native` is a separate graphics client of the verified portable Orbiter
core. It owns the window, OpenGL renderer, camera, input and wall-clock scheduler.
It runs in the same process as the core and reads copied state snapshots. It is
an internal portable client, not an implementation of the Windows GraphicsClient
plugin ABI. `orbiter-headless` retains no graphics dependency.

Current validation: local Linux Debug and Release pass 10/10 suites, including
the existing frozen-reference parity checks. Native Wayland hardware rendering
on Intel/Mesa and X11 software rendering pass the graphical integration suite.
Hosted Windows/Linux and existing Windows application checks are pending.

## Build and run

Requires CMake >=3.19, a C++17/C compiler, an OpenGL 3.3 core driver and native
window-system libraries. Python >=3.8 is required when tests are enabled, not at
runtime. GLFW 3.5.1 is fetched from its official repository with SHA256
`5234f4f29473e9a06bc7847d8371858dd135d38466eeeaa652fdc9f8f9ff0c20`.

Ubuntu development prerequisites:

```sh
sudo apt-get install build-essential cmake libwayland-dev libxkbcommon-dev xorg-dev
cmake -S Portable -B out/native -DCMAKE_BUILD_TYPE=Release \
  -DORBITER_BUILD_VIEWER=ON -DBUILD_TESTING=OFF
cmake --build out/native --parallel 2
out/native/native-client/orbiter-native \
  --scenario "$PWD/Tests/Portable/Fixtures/TwoBody.scn"
```

The root build supports the same components with `-DORBITER_PORTABLE_ONLY=ON`.
Existing `cmake -S Tests/Portable` commands remain supported. Graphics are
opt-in: omit `ORBITER_BUILD_VIEWER` for a build without GLFW or a display.
An offline build may set `FETCHCONTENT_SOURCE_DIR_GLFW` to a verified source
checkout. GLFW is linked statically; OpenGL functions are resolved through GLFW.
The client does not link Direct3D or a Windows API emulation library on Linux.

On Windows, use an MSVC x64 developer shell and `-G Ninja`. The frontend compiles
there; graphical runtime coverage depends on an available OpenGL 3.3 context.
Windows CI covers compilation, controller behavior and native numerical parity;
Linux CI additionally requires actual software-rendered graphical tests.

## Controls and supported scene

| Control | Action |
| --- | --- |
| Space | Pause/resume |
| N | Advance exactly one fixed step while paused |
| R | Reload the scenario and reset its simulation time; retain pause state |
| Tab | Switch overview/vessel-follow camera |
| Left drag | Orbit the camera |
| Mouse wheel | Zoom |
| Escape/window close | Exit and finalize trace output |

The scene contains one untextured spherical primary, an asymmetric vessel,
body-local attitude axes, an orbit trail and live telemetry. Overview enlarges
the vessel marker for visibility; follow view uses metre-scale vessel geometry.
The geometry is procedural and needs no downloaded visual assets. Follow view
uses separate depth ranges for the distant planet and nearby vessel. Camera
origins are subtracted in double precision before graphics conversion; Orbiter's
left-handed axes are converted explicitly at the rendering boundary.

The simulation supports the same [fixture subset](Tests/Portable/README.md) as
the headless milestone. Cockpits/MFDs, external meshes/textures, vessel modules,
thrust, propellant, atmosphere, terrain and ephemerides remain later work.

## Timing and trace guarantees

Normal operation runs at real time with a fixed one-second physics step by
default. Rendering interpolates completed poses with at most one tick of visual
latency; interpolation never changes the session or trace. Telemetry reports
the latest completed simulation time. Physics catch-up is bounded per frame,
with remaining work retained. Pausing discards pending wall-clock time and
resuming starts from the paused state. Camera changes never advance physics.

```sh
out/native/native-client/orbiter-native \
  --scenario "$PWD/Tests/Portable/Fixtures/TwoBody.scn" \
  --fixed-step 1 --steps 6000 --trace /tmp/native-orbit.csv \
  --smoke-test --screenshot /tmp/native-orbit.ppm --report /tmp/native-orbit.json
```

`--steps` is optional for interactive sessions. `--smoke-test` accelerates wall
clock scheduling while retaining identical physics steps. `--hidden` is available
for smoke tests; it still requires a real graphics context/display. Select a
backend explicitly with `--backend x11` or `--backend wayland`, or use the default
`auto`. `--camera overview|follow` selects the initial view. Screenshots use
binary PPM; the test tool also produces PNG copies without a third-party library.

Trace output is initialized state plus every tenth finalized step and the final
step, identical to headless execution. Reset closes the preceding segment and
starts `name.run-2.csv`, `name.run-3.csv`, etc. Input/output alias checks protect
scenario files, input scripts and other requested outputs. Invalid options,
missing assets, unsupported features, failed graphics initialization, shader/GL
errors and output-write failures return nonzero.

## Verification

Install `xvfb libgl1-mesa-dri` for Linux software-rendering tests, then:

```sh
cmake -S Portable -B out/native-tests -DCMAKE_BUILD_TYPE=Debug \
  -DORBITER_BUILD_VIEWER=ON -DORBITER_PORTABLE_COLLISION_TESTS=ON \
  -DORBITER_GRAPHICS_TESTS=ON
cmake --build out/native-tests --parallel 2
LIBGL_ALWAYS_SOFTWARE=1 xvfb-run -a \
  ctest --test-dir out/native-tests --output-on-failure
```

The nine display-independent suites include all original parity checks plus
controller/camera tests. They compare every one of 6,000 finalized states at
30/60/144 Hz and irregular frame schedules, and verify pause, single-step,
reset, retained catch-up, immutable display reads, coordinate handedness and
small camera-relative offsets at planetary distances. The tenth suite runs the
real renderer: repeated overview, scripted controls/reset/follow, and free spin.
It compares CSV bytes with headless execution, checks the immutable Windows
reference, validates image geometry, rejects invalid input/output, and records
backend/driver details and screenshots. Images are not compared byte-for-byte
across graphics drivers.

The optional smoke-test input script has lines `frame command [arguments]` with
zero-based nondecreasing frame indices. Commands use the same handlers as native
input: `pause`, `resume`, `toggle`, `step`, `reset`, `camera`, `orbit dx dy`,
`zoom amount`, `resize width height`, `exit`. It is a deterministic test interface,
not Lua support. Unexecuted events or incomplete smoke runs fail.

## Installable bundle

```sh
cmake --install out/native --prefix /tmp/orbiter-native-install
cd /tmp
./orbiter-native-install/bin/orbiter-native \
  --scenario /tmp/orbiter-native-install/share/orbiter/TwoBody/TwoBody.scn
```

Hosted bundles use tar.gz inside the GitHub artifact ZIP to preserve Linux executable permissions.
Extract the tar archive into a directory of your choice. The bundle includes both executables, the supported fixture, these instructions
and licenses. Runtime configuration paths resolve from the supplied scenario
bundle, independently of the working directory. Linux CI checks an installed
copy outside the checkout; each CI configuration archives its bundle, compiler
settings, logs, CSVs, rendering reports and screenshots.

Local development used official Ubuntu header packages extracted into a
temporary prefix because sudo required interactive authentication; no system
packages were installed by the implementation. Local hardware and software
results are recorded separately from hosted results.
