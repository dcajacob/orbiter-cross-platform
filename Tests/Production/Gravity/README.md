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
of the full application build. Accepted Windows evidence must be frozen explicitly before
porting this subsystem; no reference exists yet at this preparation stage.

Run the read-only input/source verification and comparator checks on Linux:

```sh
python3 -B Tests/Production/Gravity/capture.py verify-original
python3 -B Tests/Production/Gravity/test_comparison.py
```

These local checks do not execute the Windows implementation or satisfy capture.
