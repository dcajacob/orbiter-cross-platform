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

The repaired complete tutorial, normal four-object save and shutdown, and
matching full Windows/native mission qualification remain pending. This repair
does not change the last full-stock result or complete Phase 6. Raw evidence
remains local; Windows execution uses the local VM.
