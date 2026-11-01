# Original production terrain observations

This is a **reference-capture preparation**, not an accepted reference or a
native terrain implementation. The original `elevmgr.cpp` remains untouched.
Extraction waits for repeated native Windows Debug/Release observations to pass
the predeclared budgets. Reference files will not refresh automatically.

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
