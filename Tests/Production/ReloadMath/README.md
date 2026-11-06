# Exact-save reload math diagnosis

`Observer.cpp` is a separate diagnostic-only Windows module using the existing
read-only math observer. It selects Atlantis by default, or the explicitly
recorded `ORBITER_PHASE6_MATH_VESSEL` environment variable. Build it against the
preserved original SDK; keep its identity distinct from the original application,
control driver and reference variant. Its launch has not yet been qualified.

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
