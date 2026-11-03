# Delta-glider keyboard systems and persistence

`systems.py` runs the actual source-built DeltaGlider and DG-S in both the 2D
panel and virtual cockpit. Each case starts with the shared orbital fixture and
uses buffered flight keys: G for gear, K for nose cone, D for radiator, O and
Ctrl+O for the airlocks, U for hatch, and two B presses for full airbrakes. Two
Ctrl+B presses retract the airbrakes.

Each case uses four fresh application processes:

1. Run 24 quarter-second frames and save while all seven mechanisms are moving.
2. Reload the original scenario output and run 216 frames without further input.
   Every mechanism must start at its saved position, continue moving and reach
   its fully deployed stop.
3. Reload that scenario, close the mechanisms with the original keyboard
   controls and run 240 frames, allowing the radiator its full 50-second stroke.
4. Reload the closed result for four frames. The original `AnimState2` writer
   omits closed states; the original constructors must restore those defaults.

The checker reads actual vessel animation samples and saved subsystem position
and speed. It checks monotonic travel, intermediate positions, stopped endpoints,
all cockpit samples, complete presentation and graphics teardown, and runtime
errors. The animation indices identify mechanisms in the stock shared subsystem
construction order. Original scenario output rounds positions to four decimal
places; only the comparison between the final animation and that saved position
uses the corresponding half-unit rounding bound. A reloaded animation must
equal the parsed saved value exactly.

There are 16 real application lifetimes and 1,936 presentations in the four-case
suite. Inputs enter the native replay queue and follow the buffered vessel-key
route. The separate `CockpitControls/mouse_smoke.py --mechanisms` flow exercises
these keys through a real owned X11 window and GLFW, then verifies original
animation trajectories and scenario writers. The sibling `--panel-mechanisms`
flow uses held arrows and Ctrl+arrows to expose/select the original 2D panels,
then actual mouse presses to open and close all seven mechanisms. It verifies
paused panning, original clamps, key/focus release, complete mechanism travel
and both original scenario endpoints. Select `controls_dg_panel` or
`controls_dgs_panel`; it uses no mechanism shortcut keys. VC mechanism mouse
picking is covered by the sibling `--vc-mechanisms` flow, which uses real
Alt+arrow camera keys and observed projection of the original control quads.
It also checks Home, FOV/external camera keys, paused movement and focus release.
Wider DG subsystem acceptance remains separate. No production algorithm, accepted
reference or numerical budget changes.

The DG profile uses Alt+PageUp/PageDown for main thrust and Alt+Home/End for
hover, preserving the bare camera bindings. `thrust_profile.py` runs both
gliders in both cockpit modes through native replay input, checks independent
monotonic engine controls, original latched release and fully closed zero
stops, and verifies that bare camera keys do not fire engines.

```sh
DISPLAY=:0 python3 -B Tests/Production/CockpitControls/mouse_smoke.py \
  --case controls_dg_panel --panel-mechanisms \
  --frozen out/frozen-cockpit-controls --configuration Debug \
  --executable out/native-cockpit-engine/orbiter-production \
  --assets out/scene-resources --data out/data \
  --modules out/native-cockpit-engine/NativeModules --planets out/planets \
  --output out/real-dg-panel-mouse
```

For VC picking, select `--case controls_dg_vc --vc-mechanisms` or
`--case controls_dgs_vc --vc-mechanisms` with the same paths and a new output.
Run the separate engine-binding checks with:

```sh
xvfb-run -a env LIBGL_ALWAYS_SOFTWARE=1 GALLIUM_DRIVER=llvmpipe \
  python3 -B Tests/Production/DeltaGlider/thrust_profile.py \
  --build out/native-cockpit-engine --assets out/scene-resources \
  --data out/data --planets out/planets --output out/native-dg-keymap
```

Run with an already built, matching engine/renderer and staged stock assets:

```sh
xvfb-run -a env LIBGL_ALWAYS_SOFTWARE=1 GALLIUM_DRIVER=llvmpipe \
  python3 -B Tests/Production/DeltaGlider/systems.py \
  --build out/native-cockpit-engine --assets out/scene-resources \
  --data out/data --planets out/planets --output out/native-dg-systems
```

`--case dg_panel`, `dg_vc`, `dgs_panel` or `dgs_vc` selects an individual case.
Every output directory must be new. The full suite runs in each native
Debug/Release automatic/SSE2 CI job; its raw scenarios, inputs, traces, invocations
and lifecycle reports are archived even on failure. An isolated qualified Mesa
build can be selected through `LD_LIBRARY_PATH` for unsuppressed sanitizer runs.

## Paired preserved Windows application

`SystemsObserver/` builds `SystemsDriver.cpp` against the preserved SDK from
application source `f725194209634f7fd5d1d44d426cfa9b5e303e37`. The executable,
stock vessel DLL and graphics client remain the preserved originals. The new
observer sends `oapiSimulateBufferedKey`, reads `VESSEL::GetAnimation` and the
ordinary vessel state APIs, and saves through `oapiSaveScenario`. The same
four-process checker then inspects the original files. Original application/SDK
identity, actual dispatched keys and completion markers must match.

The native `pre` replay queues a key during the module pre-step; its next frame
consumes that queue before updating the vessel. The original SDK dispatch is
immediate. The original observer therefore dispatches at `pre` tick plus one,
matching the native consumption boundary. Both schedules are retained in the
evidence. Simulation steps, clocks and all subsystem implementations retain their
original behavior.

CI builds this observer after the existing original spacecraft observations and
runs it in Windows Debug/Release automatic/SSE2 jobs. The paired comparison
requires all four cases and all four phases, passed producer reports and exact
capture identities. It verifies evidence hashes, exact saved mechanism positions
and speeds, exact animation trajectories at every sample, corresponding CPU math
profiles, discrete vessel/cockpit state and the unchanged physical-state budgets
from `Cockpit/cases.json`. Original outputs archive selected evidence files,
excluding the staged data installation. All four build/profile capture pairs
from run 41602701454 pass these unchanged comparisons locally; the workflow's
later Help failure remains separate. [Comparison evidence](../../../Docs/Production/DGSystemsWindowsVerification.json)

On Windows, after staging the preserved runtime with `CockpitControls/prepare.py`:

```sh
cmake -S Tests/Production/DeltaGlider/SystemsObserver -B out/systems-observer \
  -G Ninja -DCMAKE_BUILD_TYPE=Debug -DORBITER_TEST_RUNTIME=out/focus-original
cmake --build out/systems-observer
python -B Tests/Production/DeltaGlider/systems.py --original \
  --executable out/focus-original/Orbiter.exe --mesa out/mesa-runtime \
  --data out/production-data --planets out/standard-planets \
  --output out/original-dg-systems
```

Compare corresponding downloaded Windows/native artifacts:

```sh
python3 -B Tests/Production/DeltaGlider/systems.py compare \
  --original original/original-dg-systems --native native/native-dg-systems \
  --output dg-systems-comparison.json
```
