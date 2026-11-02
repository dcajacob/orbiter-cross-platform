# Frozen original-runtime primitive observations

These compact tables retain the exact input/result strings from the original
Windows SDK/math observer in [run 41382988661](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41382988661),
using unchanged application/SDK `391919027ac3e4a4d42f145373c788fc859c32cd`.
The nominal observation proved its physical, propellant and animation traces
byte-identical to the existing frozen uncontrolled-impact reference. The paired
runtime experiment recorded FMA3 enabled before disabling it, and passed its
unchanged contact comparison. Neither capture uses the native math backend.

Each table has 28,800 observations: sine/cosine of rotation, latitude and
longitude, arcsine of the observed normal component, and two-argument arctangent
of normal components. All 17-digit input/result strings are preserved. Gzip
compression is lossless and has a zero timestamp. Provenance includes the hosted
artifact digest, original CSV member hash, sample counts and capture reports.

These are primitive oracles. The existing frozen flight references, all their
budgets, and the independent physical criteria remain authoritative and unchanged.
No workflow refreshes these tables automatically. Native math tests also compare
against independently rounded MPFR results at 256 and 512 bits and check signed
zero, domain errors and NaN/exception propagation.
