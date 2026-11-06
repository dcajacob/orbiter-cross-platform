# Exact-save reload math diagnosis

`Observer.cpp` is a separate diagnostic-only Windows module using the existing
read-only math observer. It selects Atlantis by default, or the explicitly
recorded `ORBITER_PHASE6_MATH_VESSEL` environment variable. Build it against the
preserved original SDK; keep its identity distinct from the original application,
control driver and reference variant. Actual original-Windows off/on captures
now have independently audited launch and private-desktop receipts. The new
observer leaves every primary physical/resource/event trace, clock, camera,
frame and saved byte identical. The fresh stock-state hash also reproduces the
retained original reference. These are diagnostics, not fresh full38 acceptance.

Before trusting it, run the same exact saved input with and without the module
and require identical original state, clocks, resources, camera, frame and saved
bytes. Compare its tick-indexed rows to the existing native `ground-math.csv`.
A diagnostic module does not repair missing historical reference receipts.

`corpus.py --trace TRACE --output NEW_DIRECTORY` reads ticks 211–243 and emits
the exact observed arcsine inputs plus 32 binary64 neighbours on each side.
The current retained trace yields 2,145 inputs. Supply `inputs.txt` to the existing
CRT diagnostic's optional `--inputs` argument. The original default CRT corpus
remains available unchanged. Preserve actual provider/version/hash and CPU/math
mode in the diagnostic output. This corpus covers `nz/asin_nz` observation only;
it does not establish the first differing physics operation or repair the reload.

The actual Windows Debug CRT and native automatic path agree on all 2,145
captured arcsine inputs and neighbours, and on 74,115 sampled touchdown
`atan2`/sine/cosine evaluations. All six vessels' reconstructed touchdown inputs
agree through tick 211. A one-ULP `hypot` difference explains the SDK lift-vector
getter difference from tick 1; that getter does not drive the physics forces.
Angular acceleration first differs at 211, before public velocity and angular
velocity at 212. These findings narrow the investigation; none is a proven fix.

`InternalObservation.h` reads each vessel and composite body's quaternions,
compensated position/velocity, cached acceleration/torque and gravity selection
through its owning headers. It requires exact public/internal position, velocity
and rotation-matrix fences before reading. Protected members use typed member
pointers, with no constructed derived object or altered runtime layout.
`compare_internal.py` requires complete ticks 1–243 and the same stable
object/kind roster, clocks and field closure. It records first differing binary64
values and never grants acceptance. Native observation/relink captures must
remain byte-identical to the complete retained 960-frame baseline with clean,
unsuppressed sanitizers before those observations are used.

Reconstructing the six vessel centres found one primitive mismatch among 8,748
samples: SRB1 longitude at tick 211, `atan2` with binary64 arguments
`c1550c2a4f069879` and `412bcfdda20e1e30`. Windows automatic returns
`bff6837bee573509`; Windows SSE2 and the old native automatic binding return
`bff6837bee57350a`. Native had compiled `atan2.c` only for SSE2. The revised
internal binding compiles the unchanged vendor source for both paths and
dispatches by the existing CPU profile. It changes no physics source or ordering.

The derived `Math/Reference/ReloadAtan2` regression fixture covers the exact pair
and 32 neighbours on each axis (4,225 pairs). Both actual Windows CRT providers
agree in each mode. The revised automatic and forced-SSE2 builds pass those
values, the 28,800 existing frozen samples per mode, MPFR and existing edge
checks. Raw CRT observations remain local. Live cache reads confirm the exact
first differing SRB1 longitude and its cosine at tick 211. Fresh source-bound
sanitizer packages at `81dcc014` pass all sixteen focused native writer/reload
runs: four profiles, two repetitions, unchanged complete state, clocks, camera,
frame and saved-content checks. The consolidated coordinator independently
re-read all eight completed stages. Current-Windows qualification and the final
full campaigns remain separate gates.
