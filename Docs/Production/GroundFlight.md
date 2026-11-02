# Phase 5 ground-flight validation

The native flight host uses the production `PlanetarySystem`, Earth/SPICE and
atmosphere, terrain/contact code and source-built stock ShuttlePB. Local Debug
now passes all seven frozen ground cases and the additional controlled upright
landing. Hosted Ubuntu 24.04 Debug/Release now passes with automatic and forced SSE2
math. Current Windows application/SDK/client/reference checks also pass.
Attachment and vessel lifetime integration keep Phase 5 open; the stock-playable
release remains incomplete.

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

## Hosted qualification

[The native client matrix](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41387877919)
passes all four combinations of Debug/Release and automatic/SSE2 math at
`85b3cf3e`. Every combination passes primitive/MPFR checks, real scene/image
comparison, six orbital flight cases, twenty sessions, actual keyboard events,
controlled upright landing and all seven ground cases. Both rendering intervals
produce identical numerical histories and checkpoints within each configuration.
The largest observed impact attitude difference is 4.70e-6 rad, below 0.001 rad;
controlled-flight propellant differences remain below 1.87e-10 kg.

The same numerical source passes the current
[Windows application/SDK and real OpenGL client](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41387877934),
[original production orbit/propulsion and fourteen behavior references](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41387877944),
[portable Windows/Linux comparisons](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41387877926)
and [SPICE parity](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41387877921).
The [terrain/world matrix](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41388594785)
passes at `879d14ef`, which only adds the missing test-oracle package to that
workflow. Numerical, SDK, renderer and test sources are identical to `85b3cf3e`.

[The evidence record](NumericalRuntimeVerification.json) preserves run/source
identities, all four downloaded and SHA256-verified native artifact digests,
Windows client artifact digests, reported numerical profiles, measured errors
and local preview identity. Hosted artifacts contain full traces, logs, images,
reports, loaded modules/assets and build metadata, retained for 90 days. This
record is an observation report and cannot replace a frozen reference.

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

## Remaining Phase 5 integration

Ground-flight parity does not close the whole phase. The frozen original
`attachments` and `lifetime` cases still need native application comparisons:
real child-vessel creation, attach/detach, live focus changes and deferred
deletion with matching visual/module lifetime. The current native application
explicitly rejects pending dynamic deletion. Twenty full session reloads cover
world replacement, not these in-session object transitions.

These are the next interaction gates before declaring Phase 5 complete.
Phase 6 cockpit/HUD/MFD/Delta-glider work has not started.

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
Cockpit and flight instruments remain Phase 6 work. The prepared laptop snapshot
is the clean Ninja build of `85b3cf3e`; it passes an outside-checkout launch with
120 ticks, eight presents and complete graphics teardown. Earlier immutable
snapshots remain available.
