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
