# Native ShuttlePB orbital flight

The production external-view host now has interactive ShuttlePB flight controls,
a real-time clock independent of rendering, pause and single-step, time
acceleration, automatic docking and manual undocking, and stock scenario
quicksave/reload. It retains the actual Sol/SPICE world, stock ISS, source-built
ShuttlePB and separately built shared OpenGL renderer.

This delivery covers the reduced Earth-orbit ISS/ShuttlePB fixtures. Cockpit,
HUD/MFD instruments, Delta-glider, atmospheric flight/contact acceptance, Lua,
normal Orbiter recording/playback, sound, general stock scenarios and installed
release packaging remain later gates. The title bar reports original vessel
state; original instruments still require their own integration.

## Run the prepared laptop build

```sh
Tests/Production/Flight/run-local.sh
```

Start paused; Space resumes. `--run` starts immediately. The launcher resolves an
immutable matching build snapshot and absolute data roots, so the working
directory does not matter. Rebuilding creates a new snapshot without overwriting
libraries mapped by an already running application.

| Action | Laptop preset |
| --- | --- |
| Increase/decrease main throttle | Page Up / Page Down |
| Cut main/retro thrust | Backspace |
| Increase/decrease hover throttle | Home / End |
| Pitch up/down; translate up/down in linear mode | W / S |
| Yaw left/right; translate left/right in linear mode | A / D |
| Bank left/right in rotation mode | Z / C |
| Translate backward/forward in linear mode | Z / C |
| Select rotation/linear RCS mode | F |
| Toggle RCS off/on | Ctrl-F |
| Reduced RCS power | Hold Shift with the direction key |
| Kill rotation | K |
| Toggle altitude hold | Ctrl-A |
| Prograde / retrograde | [ / ] |
| Orbit normal / antinormal | ; / ' |
| Pause/resume | Space or Ctrl-P |
| Increase/decrease time acceleration | T / R |
| Undock from ShuttlePB's port | Ctrl-D while running |
| Quicksave / reload saved scenario | Ctrl-S / F5 |
| Advance one physics tick while paused | F6 |
| Orbit camera / zoom | Right-drag / wheel |
| Close | Escape |

RCS direction keys are momentary: hold to fire, release to stop firing. Motion
continues after release until an opposing force or torque changes it. Main and
hover throttle settings persist. Autopilots can command thrust independently.
The laptop preset moves altitude hold from A to Ctrl-A so the left RCS key
cannot accidentally enable it.

The title bar shows actual simulation time, main/hover throttle, fuel, RCS mode
and power, active autopilots, ISS range and docking state. Saves default to
`$XDG_DATA_HOME/orbiter/Scenarios/Quicksave.scn`,
or `$HOME/.local/share/orbiter/Scenarios/Quicksave.scn`; `--save PATH` overrides it.
Quicksave writes only finalized states through original `State::Write`,
`Camera::Write` and `PlanetarySystem::Write`/vessel module serializers. Reload
replaces the world and graphics session in the same process and preserves pause.
A pending single-step completes before its quicksave is committed.

`--keymap PATH` selects an original-format Orbiter keymap. Space, F5, F6 and Escape
are native host actions. The original numeric-keypad flight bindings remain
available when invoking the executable without the laptop override.

Raw joystick input uses original directional control logic: axes 0/1 for
bank/pitch, axis 2 for yaw/lateral control, and the third button for alternate
X-axis yaw control. `--joystick-twist-axis N` overrides axis 2. Device throttle
is opt-in with `--joystick-throttle-axis N` and arms after movement; indices are
zero-based. Hardware controller testing remains separate from keyboard acceptance.

## Timing, control and resource boundaries

Interactive execution accumulates `steady_clock` wall time and advances original
`TimeData` and `Session` at a fixed quantum, default 1/60 second. Time acceleration
uses original `TimeData::SetWarp`, with the original 0.1–100,000 limits. Backlog
is retained. Rendering and window visibility cannot discard simulation time.
The original world/callback/finalization ordering and propagation remain shared.

`FlightControls` retains original key mappings, keyboard throttle/RCS/trim/brake
formulas, joystick direction mapping and buffered vessel commands. It delegates
to the existing vessel methods and gives the actual module its key callbacks.
`flight_source.py` checks these against the preserved Windows source. The public
Windows SDK and `VECTOR3` layout are unchanged.

`--frames` retains the earlier deterministic capture mode. `--ticks N
--render-every K` runs recorded test commands with different rendering
frequencies. These bounded modes ignore live flight/camera input; the close
button remains available. Test command CSVs specify host tick, before/pre/after
phase, SDK action and value. Host ticks include paused ticks. This test facility
has separate evidence from normal Orbiter recording/playback.

## Verification

Additional immutable [Windows references](../../Tests/Production/FlightReference/README.md)
were captured before native flight integration, using the verified application
at `39191902` and driver at `a72fabef`. Both MSVC configurations repeat identically
and agree. Existing two-body, fourteen-case behavior and image references remain
unchanged, with unchanged budgets.

Local Debug results on the Intel/Mesa laptop:

- Main/hover thrust, all twelve RCS directions, five orbital autopilot modes,
  docking/undocking, pause/warp and ShuttlePB persistence match Windows with zero
  measured state differences.
- Rendering every 4 versus every 17 ticks produces byte-identical state traces
  and identical serialized checkpoints.
- Twenty sixty-frame sessions in one process present successfully, register and
  unregister real Earth/ISS/PB visuals, release their contexts and produce
  identical initialized/stepped states.
- Actual X11 keyboard events reach the production vessel, consume propellant,
  change RCS velocity, pause/step, save and reload in process. The same check
  passes under isolated Xvfb/llvmpipe.
- The unchanged scene passes on Wayland and X11/XWayland with SSIM
  0.9862598209696377, zero landmark error and unchanged numerical budgets.
- All thirty portable tests and the original source-conservation audits pass.

Local ASan/LSan/UBSan vessel parity and repeatability also pass; this is
separate from GPU sanitizer coverage. Hosted Ubuntu 24.04 Debug/Release passes at
`db1d7fa19055ef3ba6a9bfff37e50bf5c61b79c0` in
[run 41354276713](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41354276713):
original image/state parity, all flight cases, twenty complete sessions and actual
keyboard control/save/reload under llvmpipe. The same source passes current
Windows application/SDK and real-client execution in
[run 41354276716](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41354276716):
both MSVC configurations, normal teardown, frozen numerical comparisons and
SSIM 1.0 against the unchanged Windows scene. The full
[production-reference workflow](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41354276705)
also passes both application builds, original two-body/orbit/propulsion references,
fourteen repeated behavior cases and Debug/Release numerical/lifecycle comparison.
The same source passes
[portable tests](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41354276718),
[world/terrain regressions](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41354276706)
and [native SPICE parity](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41354276727).
These results establish the orbital flight delivery; the complete stock release,
controller hardware and performance gates at 1920×1080 remain open.

The hosted native artifacts retain full traces, input/event logs, scene captures,
loaded-module/asset hashes, build metadata and licenses for 90 days:

| Artifact | SHA256 of original ZIP |
| --- | --- |
| [Release](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41354276713/artifacts/13102927025) | `96f77e1cf52413a231eef57b4715d1eb4743648de36c07349d6d5a8298269239` |
| [Debug](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41354276713/artifacts/13102332842) | `ef5637ca9766bc9e1a71e4d67c00a61c1e3d5b8b84ca8650abe251e7c12268a0` |

## Reproduce and prepare a stable preview

Build the production engine/modules and separate renderer as described in
[NativeExternalView.md](NativeExternalView.md), then:

```sh
python3 -B Tests/Production/Flight/prepare-preview.py \
  --build out/native-vessels --destination out/native-flight-preview
python3 -B Tests/Production/Flight/verify.py \
  --executable out/native-vessels/orbiter-production \
  --assets out/native-scene-resources --data out/native-celestial-data \
  --modules out/native-vessels/NativeModules --planets out/archive-data \
  --configuration Debug --output out/native-flight-verification
```

The native client CI workflow runs original scene/image parity, flight parity,
twenty complete sessions and real keyboard interaction under software OpenGL in
Ubuntu 24.04 Debug/Release. The existing Windows application/client, SDK, portable,
world/terrain and SPICE workflows continue independently.

The keyboard regression also holds and releases all six keys in both RCS modes,
at full and reduced power, and verifies release on focus loss. It checks actual
finalized thruster/exhaust levels in `thrust-state.csv` against the per-tick input
log, and rejects unintended autopilot or main/hover activation. The thrust trace
records completed physics ticks separately from host input ticks (which include
paused ticks); power values are fractions of full thrust. RCS power is the
maximum of the twelve actual RCS group levels, and exhaust power is the maximum
of the vessel's declared exhaust levels. Stock ShuttlePB declares main/hover
exhausts, without a separate exhaust visual for each RCS jet.

The laptop-keymap follow-up was reproduced locally with the old A binding:
releasing A left altitude hold enabled and the hover engine firing. With Ctrl-A,
all 24 hold/release combinations and focus loss pass under Xvfb/llvmpipe, with
384 finalized idle samples at zero RCS/exhaust power. The six frozen flight
comparisons pass their unchanged budgets (maximum position difference
0.0000019073522708 m), both rendering frequencies agree, twenty complete sessions
pass, and all thirty portable tests pass. These are local follow-up results;
the hosted runs linked above describe the earlier `db1d7fa1` delivery.
