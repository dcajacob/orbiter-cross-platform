# Portable core and headless parity milestone

Goal: run one unpowered vessel for 6,000 fixed one-second steps on native Linux
and Windows, using shared original Orbiter propagation code, and compare 601
samples against a frozen pre-refactor Windows reference.

**Current stage: pre-refactor Windows reference capture.** Hosted portable tests
pass on x64 Linux/GCC and Windows/MSVC in Debug and Release (five CTest targets
per job). The native scenario
runner and physics extraction are intentionally gated on a validated Windows
reference. There is no frozen reference or native runner yet. Local tests of the
trace tools use explicitly synthetic analytical inputs; these are never engine
traces or evidence of cross-platform simulation parity.

## Local verification

Requires a C++17 compiler, CMake >=3.19, Python >=3.8, and the existing upstream
Catch2 dependency when collision tests are enabled. Catch2 is pinned to
`b9853b4b356b83bb580c746c3a1f11101f9af54f`.

```sh
cmake -S Tests/Portable -B /tmp/orbiter-portable-release \
  -DCMAKE_BUILD_TYPE=Release -DORBITER_PORTABLE_COLLISION_TESTS=ON
cmake --build /tmp/orbiter-portable-release --parallel 2
ctest --test-dir /tmp/orbiter-portable-release --output-on-failure
```

Use a separate directory and `-DCMAKE_BUILD_TYPE=Debug` for Debug. Offline builds
can add `-DFETCHCONTENT_SOURCE_DIR_CATCH2=/path/to/verified/Catch2`.
CTest runs math, collision, VECTOR3 layout, trace I/O, and trace-tool validation.
Python is a test/capture dependency, not a future simulation runtime dependency.

## Original Windows reference capture

The dedicated **Portable Core and Windows Reference** workflow builds the
portable tests with GCC/Linux and MSVC/Windows, x64 Debug and Release. Its manual
`capture_windows_reference` input additionally builds the original Windows
application and existing tests, then captures reference candidates on Windows.
Existing application workflow sources are unchanged. The initial hosted run is
[41175171274](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41175171274),
executing source commit `c2ce0f61db2cbac58e7281a87787c3faa2eaf365`.

The capture job requires a clean committed checkout and verifies the numerical
source files against upstream commit
`8e6ae437901417eef56f08b8f969ff92df83db5e` before executing. It preserves actual
source, fixture, binary and provider hashes, compiler version, CMake settings,
commands, application logs, test logs and trace validation reports. Capture
outputs must use a new directory; an existing capture is never overwritten.

For a Windows development environment with the normal upstream prerequisites:

```powershell
cmake -S . -B out/reference-app -G Ninja -DCMAKE_BUILD_TYPE=Release `
  -DCMAKE_C_COMPILER=cl -DCMAKE_CXX_COMPILER=cl `
  -DORBITER_BUILD_D3D9CLIENT=ON -DORBITER_BUILD_XRSOUND=OFF `
  -DORBITER_MAKE_DOC=OFF -DORBITER_MAKE_TESTS=ON `
  -DORBITER_PORTABLE_REFERENCE_CAPTURE=ON "-DDXSDK_DIR:PATH=$env:DXSDK_DIR"
cmake --build out/reference-app --parallel 2
ctest --test-dir out/reference-app --output-on-failure
cmd /c "cl 2>&1 & exit /b 0" | Set-Content out/reference-app/compiler.txt
python Tests/Portable/capture_windows_reference.py `
  --source . --orbiter out/reference-app/Orbiter.exe `
  --output out/reference-release-candidate --configuration Release
```

Repeat from a separate Debug build and output directory. Build D3D9Client with
the original application because LuaInterpreter
unconditionally includes its generated `gcCoreAPI.h`. This is a build-time
requirement of the existing Windows test graph; reference runtimes do not load
a graphics-client plugin, and the native runner will not link graphics code.
The workflow captures build logs automatically. Hosted runs use the authorized public destination,
https://github.com/dcajacob/orbiter-cross-platform. The `upstream` remote retains
official Orbiter; `origin` identifies this portability project.

Each capture stages a fresh isolated runtime for every run. It never changes an
installed Orbiter, the original build's configuration, or source fixtures. The
Windows original loader needs a test-only `PortableFixedPrimary.dll` to supply
the root body's static initial state; otherwise it falls back to uninitialized
orbital elements. The provider returns a fixed position `(100000000,0,0)` m and
zero velocity. The nonzero global translation avoids the original celestial
interpolator's zero-vector normalization; all scenario and trace positions are
primary-relative. The provider has no force or vessel propagation code, no data
downloads, is disabled in normal builds, and is not installed with the app. The
future native runner does not need a DLL. No original numerical source is changed
to accommodate this fixture.

The fixture has primary mass `5.972e24 kg`, vessel mass `1000 kg`, isotropic
inertia, radius `7000000 m`, epoch MJD `51544.5`, and circular speed
`7544.9801173646956 m/s`, calculated using Orbiter's historical
`Ggrav = 6.67259e-11`. RK4 has one substep; stabilization, wind, radiation,
collisions, distributed mass and nonspherical gravity are disabled. There is no
atmosphere, mesh, vessel module, thruster, propellant, or scenario script.

Capture performs two identical orbit runs, a half-step run (12,000 steps at
0.5 seconds), and two free-spin runs (`1e-4 rad/s` about body z, 6,000 seconds).
It checks complete sampling, exact elapsed time, repeatability, analytical
position/velocity/attitude, energy/angular-momentum drift, and half-step
convergence. The original quaternion update is retained; free-spin accuracy is
checked rather than assuming all angular propagation is fourth order.

## Trace contract and numerical budgets

Observation is disabled by default. Original Windows app options:

```text
Orbiter.exe --scenariox=TwoBody --fixedstep=1 --maxframes=6000 \
  --physics-trace=trace.csv --trace-vessel=Probe --trace-primary=Primary
```

The CSV uses an ASCII header, classic locale, LF newlines and 17-digit double
precision. Fields are:

```text
step,sim_seconds,mjd,rx,ry,rz,vx,vy,vz,qx,qy,qz,qw,wx,wy,wz
```

Positions are metres and velocities metres/second relative to the primary, in
Orbiter's global ecliptic axes. Quaternions use vector x/y/z then scalar w and
map local vessel axes to global axes. Angular velocity is radians/second in
vessel-local axes. Scenario AROT and VROT retain their original degrees and
degrees/second interpretation. Rows represent initialized state and every tenth
fully finalized step; at the default run length there are 601 rows.

```sh
python3 Tests/Portable/trace_tools.py candidate.csv --reference frozen.csv
python3 Tests/Portable/trace_tools.py spin.csv --spin 0.0001
```

Vector errors use Euclidean norms. Rotation comparison ignores quaternion sign
and uses a chord-angle calculation accurate near zero. Quaternions must have
unit norm within `1e-12`; normalization cannot hide invalid traces.

| Quantity | Maximum error |
| --- | --- |
| Position | `0.01 m` |
| Velocity | `1e-5 m/s` |
| Orientation angle | `1e-8 rad` |
| Angular velocity | `1e-10 rad/s` |
| MJD | `1e-10 days` |
| Relative energy and angular momentum drift | `1e-8` |

Step indices and elapsed seconds must match exactly. A half-step run must
reduce maximum analytical position and velocity errors by at least a factor of
two, allowing numerical noise floors of `2e-7 m` and `2e-10 m/s`. These budgets
are requirements, not measured engine results. Failure blocks the refactor;
tolerances must not be silently loosened.

## Freeze gate and remaining implementation

The workflow uploads candidates and evidence for 14 days. A successful capture
has status `candidate_passed_requires_review`; Debug/Release candidates must
also agree. Review the original-app test results, source/configuration hashes,
analytical budgets, repeatability and convergence before committing the accepted
orbit/free-spin CSVs and provenance under `Tests/Portable/Reference`. Preserve
the capture commit and record the acceptance commit. No automatic baseline
refresh is permitted. There are deliberately no reference CSVs in this checkout.

Only after that gate passes:

1. Separate orbital-element time/configuration inputs, retaining Windows
   adapters; cover circular, eccentric, inclined and hyperbolic trajectories,
   epoch changes, and state/element round trips.
2. Extract the required body-state, gravity and RK4 paths into a shared portable
   core without changing formulas, ordering or state finalization.
3. Add the internal load/step/read-state session and `orbiter-headless --scenario
   <path> --fixed-step 1 --steps 6000 --trace <path>`, with explicit asset paths,
   standard file access, unsupported-feature errors and no graphics dependency.
4. Run x64 Debug/Release on Windows and Linux, compare all samples with the
   frozen references and each other, archive reports, and keep original Windows
   application builds/tests passing. Mark the milestone complete only then.
