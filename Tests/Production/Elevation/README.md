# Original production terrain observations

The original Windows reference is **accepted**; this is not yet a native terrain
implementation. [Run 41292909453](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41292909453)
passes Debug and Release with byte-identical repeats and zero cross-build error
at source `c1fb3fad`. [Reference provenance](Reference/provenance.json) preserves
all original artifact bytes, per-member hashes, compiler/build output, runtime
identity, logs, traces and comparison results. Reference files never refresh
automatically. Verify them with:

```sh
python3 -B Tests/Production/Elevation/frozen_reference.py
```

Preparation run `41292582063` exposed a missing `ORBITER_MODULE` declaration in
the observation plugin, so the legacy loader did not dispatch its callbacks.
It is a failed setup attempt, not an accepted terrain run. The declaration is
corrected; no production terrain source, query or budget was changed.

The observer loads the accepted source-built Windows application/SDK from
`2e8bbbf2`, using real Sol, ISS and ShuttlePB plus the original verified data and
standard Earth/Moon/Mars elevation archives. It calls the existing production
`oapiSurfaceElevationEx`; no renderer is loaded. Application startup, two physics
frames and normal session shutdown still run through the original application.

Each interpolation mode records 2,040 queries: 85 global/landing-site/seam
locations on three real planets, four requested resolutions, and both the
manager-owned cache and an explicit SDK cache. It records metres, local terrain
normals and actual loaded levels. Longitude/latitude inputs are degrees, then
converted with Orbiter's original `RAD`. Each mode executes twice in separate
processes; repeats must be byte-identical. Debug/Release heights must agree to
`1e-6 m`, normal components to `1e-10`, and all discrete inputs/levels exactly.
Every body must supply finite, nonflat terrain and unit normals.

The original Config accepts explicit linear mode 1; cubic interpolation is its
default mode 2, whose explicit selection the original parser does not accept.
The capture preserves that behavior. It verifies immutable runtime files,
original source/input hashes and both data profiles before querying. Compilation
or Linux results cannot substitute for Windows application execution.

The dedicated `production-elevation.yml` captures logs, toolchain output, input
identity, repeated CSV files and comparisons. A passing capture must be frozen
and independently verified before changing elevation calculations or file access.
