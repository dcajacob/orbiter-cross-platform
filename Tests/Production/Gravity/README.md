# Production nonspherical-gravity reference capture

This is a pre-extraction observation of the actual `PinesGravProp` compiled from
`Src/Orbiter/PinesGrav.cpp`. Its source and header still match the original
production revision `38b7c627`. No force formula, coefficient or coordinate
conversion is changed for the capture. It is not a replacement gravity model,
production world initialization or contact/scenario acceptance case.

A supplementary normalized J2-only fixture checks the analytical gradient of
the quadrupole potential at all twelve directions, to `1e-12 m/s²`. It does not
replace the stock model queries or alter the production implementation.

The protocol locks the tracked Earth EGM96 and lunar JGL165 coefficient bytes,
driver and comparison source, and original production source hashes. Each
Windows Debug/Release executable runs twice and must produce byte-identical
864-row traces. Query degrees are 2, 4, 12 and 32; orders are zero, half-degree
and full degree. Twelve directions at three radii per body include positive and
negative coordinate axes, poles, an almost polar direction and inclined points.

Inputs use Pines' right-handed body-fixed axes in kilometres. CSV accelerations
are the perturbation only, in m/s²; the point-mass contribution is excluded by
the original implementation. This does not exercise `PlanetarySystem`'s external
left-handed/world transformation. Before extraction, Debug/Release must satisfy
the predeclared Euclidean acceleration budget of `1e-12 m/s²` absolute plus
`1e-10` times the reference magnitude, with exact query identities/positions.
These force-query budgets supplement the unchanged orbit/contact budgets.
A failed baseline blocks extraction; thresholds must not be widened to pass.

The Windows production test build produces `production-gravity-observer.exe`:

```sh
python Tests/Production/Gravity/capture.py capture \
  --executable out/production-app/production-gravity-observer.exe \
  --output out/production-gravity --configuration Release
```

The output directory must be new. Capture never writes an accepted reference.
The production workflow archives both traces, logs and source/input/executable
metadata alongside compiler settings and full application metadata, then compares
Debug/Release. A small independent Windows build executes the identical source
without building the application; its outputs must also match each configuration
of the full application build.

The [accepted Windows reference](Reference/provenance.json) comes from source
`d85fc0b8` and [hosted run 41280522652](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41280522652).
All four builds produced the same trace bytes (SHA256
`87b154d6212f742556f610ab42b4b9a6708555bcfc878b7acafa50760d198173`),
and all twelve analytical checks passed in each run. The evidence includes
original standalone artifacts and filtered full-application build/trace archives,
with original GitHub artifact digests and every preserved member's hash. No
compiled binaries are added to Git. The initial standalone macro-definition
failure is recorded separately and is not accepted as numerical evidence.

Reference acceptance is explicit; no command refreshes it. Verify all archived
members, repeat equality and cross-build budgets offline with:

```sh
python3 -B Tests/Production/Gravity/frozen_reference.py
```

On the original capture checkout, run the read-only input/source verification
and comparator checks on Linux:

```sh
python3 -B Tests/Production/Gravity/capture.py verify-original
python3 -B Tests/Production/Gravity/test_comparison.py
```

These local checks do not execute the Windows implementation or satisfy capture.
