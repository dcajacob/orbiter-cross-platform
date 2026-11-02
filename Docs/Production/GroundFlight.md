# Phase 5 ground-flight validation

The native flight host uses the production `PlanetarySystem`, Earth/SPICE and
atmosphere, terrain/contact code and source-built stock ShuttlePB. Local Debug
now passes all seven frozen ground cases and the additional controlled upright
landing. Hosted qualification of this numerical fix is still required. Phase 5
and the stock-playable release are not declared complete by these local results.

## Frozen original Windows evidence

[Run 41368023101](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41368023101)
executes the original Windows application and SDK at
`391919027ac3e4a4d42f145373c788fc859c32cd`, using controls at `1c930be8`.
All seven cases repeat identically in both MSVC configurations and pass their
predeclared cross-configuration budgets. Original bytes and provenance remain
in `Tests/Production/GroundReference`.

The additional [controlled landing reference](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41374941546)
passes original Windows Debug/Release repeats and comparison. Its inputs,
physical criteria and unmodified traces are separately frozen in
`Tests/Production/ControlledReference`. No older reference was replaced.

All fixtures, control schedules, original drivers, reference archives and
comparison budgets remain unchanged. Capture workflows are manual-only; the
verifiers check their frozen source/member/archive hashes before comparison.
The existing two-body and orbital references remain unchanged as well.

## Local integrated results

The automatic FMA3 build passes every ground case at rendering intervals of 4
and 17 ticks. Numerical histories and serialized checkpoints are byte-identical
between rendering frequencies. Original world/finalization/time ordering and
actual control-surface animations agree with Windows.

| Case | Result against original Windows |
| --- | --- |
| Resting landed vessel | Zero measured state error |
| Atmospheric propulsion | Zero measured state error |
| Elevator/aileron controls | Zero measured state error; actual mesh animations agree |
| Unpowered contact | Pass; maximum velocity difference 4.17e-11 m/s |
| Preserved uncontrolled takeoff/impact | Zero measured state error; all six contact ticks agree |
| Landed save/reload | Zero measured comparison error; original serialization precision checks pass |
| Controlled upright takeoff/landing | Pass; liftoff/touchdown ticks 60 and 2348 agree |

The old `pb_takeoff_landing` schedule finishes inverted, approximately 149 degrees
from radial upright in both applications. It is retained as an impact regression;
its landed status does not qualify safe landing support.

The additional controlled flight uses Orbiter's original horizon and hover-altitude
programs: target 12 m above terrain, target zero at 20 seconds, then disable both
programs and hover thrust at 80 seconds. It completes 6,000 steps of 1/60 second,
reaches 10.6748 m, touches down at 0.6812 m/s and stays within four degrees of
upright. The original SDK reaches its actual landed state and saves
`STATUS Landed Earth`.

| Controlled-flight quantity | Maximum FMA3 difference | Existing budget |
| --- | ---: | ---: |
| Position | 7.46e-9 m | 1 m |
| Velocity | 1.88e-7 m/s | 0.1 m/s |
| Rotation | 5.62e-9 rad | 0.001 rad |
| Propellant | 1.14e-11 kg | Approximately 7.4e-6 kg |

Forced SSE2 also passes both previously failing flights, at both rendering
frequencies. Its impact attitude difference is 2.45e-6 rad and controlled-flight
propellant difference is 6.95e-11 kg, within the unchanged budgets. Local primitive
tests independently qualify both CPU paths against Windows and MPFR.

The six existing orbital flight comparisons and twenty complete sessions also
pass. The scene repeats with SSIM 0.9881491504 and zero projected-landmark error.
Actual keyboard checks pass all 24 RCS hold/release combinations, focus release,
aerodynamic mode/surface release, pause/step and in-process save/reload. Portable
CTest passes 31 Debug and 32 Release tests.

The integrated evidence is under `out/native-ground-reference-fix`,
`out/native-controlled-reference-fix`, `out/native-ground-sse2` and
`out/native-controlled-sse2`. These are local laptop results, separate from
hosted Ubuntu 24.04/MSVC qualification.

## Why the earlier comparisons failed

Earlier hosted checks reproduced two failures: uncontrolled-impact attitude and
controlled-flight mass/propellant. The investigation located different primitive
math rounding and a process-wide RNG whose algorithm and foreign-library draws
changed the original update/accumulation schedule. The integrated fix supplies
private numerical bindings while retaining all existing force calculations and
ordering. [NumericalRuntime.md](NumericalRuntime.md) records the pinned MIT
sources, original Windows observations, CPU dispatch, source-conservation proof
and independent qualification. Production does not use the diagnostic
process-wide interception experiments.

Historical failing evidence remains available in
[run 41371271692](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41371271692)
and [run 41376965467](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41376965467).
The read-only [intermediate force probe](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41380213246)
and [math/scheduling observer](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41382988661)
proved their original physical traces unchanged before accepting observations.
Those diagnostic runs cannot replace flight acceptance.

## Reproduce

Build matching production engine/modules and the separate renderer as described
in [NativeExternalView.md](NativeExternalView.md), then run with a real display
or an owned Xvfb/llvmpipe display:

```sh
python3 -B Tests/Production/GroundFlight/frozen.py
python3 -B Tests/Production/ControlledLanding/frozen.py
python3 -B Tests/Production/GroundFlight/verify.py \
  --executable out/native-vessels/orbiter-production \
  --assets out/native-scene-resources --data out/native-celestial-data \
  --modules out/native-vessels/NativeModules --planets out/archive-data \
  --configuration Debug --output out/native-ground-verification
python3 -B Tests/Production/ControlledLanding/verify.py \
  --executable out/native-vessels/orbiter-production \
  --assets out/native-scene-resources --data out/native-celestial-data \
  --modules out/native-vessels/NativeModules --planets out/archive-data \
  --configuration Debug --output out/native-controlled-landing
```

The native CI matrix runs Debug/Release with automatic and forced SSE2 math,
actual software-rendered scenes, unchanged image/state budgets, orbital flight,
twenty sessions, actual keyboard events, controlled landing and all seven ground
cases. Reports retain the actual numerical profile, modules, assets, images,
traces and build settings. Windows application/SDK/client checks remain required.

## Ground preview

```sh
python3 -B Tests/Production/Flight/prepare-preview.py \
  --build out/native-vessels --destination out/native-ground-preview
Tests/Production/GroundFlight/run-local.sh
```

The launcher resolves an immutable matching binary snapshot. It starts paused
at Edwards on actual stock Earth data with the real ShuttlePB module. Space
resumes; Home/End increase/decrease persistent hover throttle. W/S, A/D and Z/C
are momentary RCS controls: hold to fire and release to stop. F selects RCS mode,
Ctrl-F disables/enables RCS, and Alt-F toggles aerodynamic controls. The title
reports actual flight status, terrain height, airspeed, fuel, thrust and autopilots.
Cockpit and flight instruments remain Phase 6 work. A pre-fix preview remains
experimental until explicitly replaced with a verified matching snapshot.
