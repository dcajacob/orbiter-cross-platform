# Recorded attitude playback

The complete, unchanged four-object `DG to the moon` tutorial reached lunar
approach in the native Release/SSE2 sanitizer build at `bf36e351`. It then exited
with `Nonfinite flight state` at simulation time `307540.40009604016`: the
recorded GL-01 rotation became NaN. The original scenario, all seven recording
files, failed run and its source/runtime inputs remain preserved locally.

The recording's two horizon-frame Euler samples straddle a near-half-turn
rotation. The original matrix-to-quaternion trace branch loses unit length,
giving an endpoint dot product of `1.0000016936590066`. The original quaternion
interpolation passes that value to `acos`. The frozen Windows x64 implementation
at `38b7c627` reproduces the NaN in both automatic and forced-SSE2 math modes.
These scalar Windows observations are not a complete Windows mission run.

`Production/RecordedAttitude.h` guards the recorder's two interpolation sites.
It retries a finite out-of-domain dot product with normalized endpoint copies;
rounded coincident or antipodal unit endpoints use the continuous linear limit.
In-domain pairs call the original interpolation unchanged. Nonfinite and
zero-length inputs retain the original failure behavior. The original quaternion
primitives, Euler conversion, physical propagators, recordings, reference results
and comparison budgets remain unchanged.

`Production.RecordedAttitude` compiles the actual recorder Euler conversion and
unchanged production quaternion implementation. It checks the captured failing
pair, an independent 85-digit rotation calculation, all 2,998 original GL-01
attitude samples at eight interpolation fractions, and coincident, antipodal and
invalid-input controls. Local Linux and Windows automatic/SSE2 checks preserve
23,960 finite original results bit for bit and recover 16 nonfinite results.
The captured-pair rotation error is approximately `4.2e-12` radians, within the
existing `1e-8` budget. Linux sanitizer checks and the 622-file extraction audit
pass.

The repaired native Release/SSE2 application at `84706794` subsequently ran the
unchanged four-object playback through the final tutorial note interval at
simulation time `308760`, saved all four vessels, and exited normally after
95,112 successful presents. All observed flight states remained finite. The
665 guarded source, runtime and recording inputs were unchanged, and
unsuppressed ASan, UBSan and leak checks reported no findings.

The automatic mission check failed: GL-01's save reports `Orbiting Moon`, with
ground contact and about `0.65 m/s` of motion. An unedited reload followed by
120 seconds of natural physics also retained that status, ending at about
`0.57 m/s`. The shared original landing code distinguishes surface contact from
the settled landed state and requires five seconds of sufficiently little
movement. The failed report remains preserved, including an initial
screenshot-capture timing failure that stopped before the continuation finished.

The same actual four-object save subsequently completed 7,200 original Windows
Release/SSE2 steps in the local VM, with the matching application, SDK, modules
and renderer. The observer read state and requested the final stock save; it
did not set vessel state or change landing thresholds. Windows also retained
`Orbiting Moon`, ending at `0.5703188176 m/s`, compared with native
`0.5703145958 m/s`. Simulation time and MJD match at all 7,201 sampled ticks,
and every vessel's ground-contact flag agrees at every tick. GL-01's largest
airspeed difference is `7.061e-6 m/s`; its largest position-component difference
is `4.578e-5 m`. The Windows process exited normally after 7,200 successful
presents. This comparison establishes the behavior of the saved-state
continuation; it is not a complete Windows recording run.

Taking control through the original comma and period wheel-brake keys stops
the native vessel. A real Wayland interaction holds both brakes for 15 seconds,
uses Ctrl+S, and exits normally. GL-01 then saves as `Landed Moon` at
`Brighton Beach:1`, and all four original objects remain present. The application
completes 355 successful presents with clean unsuppressed sanitizer and context
teardown. A separate unedited, paused reload of that actual landed save renders
all four vessels and closes normally after 60 presents. The original mission
save, recordings and physics remain unchanged; the brake input is a distinct
interactive continuation, not a replacement pass for the failed automatic
mission assertion.

The matching full Windows/native recording comparison and complete four-profile
mission qualification remain pending. The current Windows application builds and all
28 standalone checks passed in both Release and Debug in the local VM, including
`Production.RecordedAttitude`; those checks do not replace a full mission.
This repair does not change the last full-stock result or complete Phase 6.
Raw evidence remains local; Windows execution uses the local VM.
