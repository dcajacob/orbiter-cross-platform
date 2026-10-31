# Portable core and headless parity milestone

Goal: run one unpowered vessel for 6,000 fixed one-second steps on native Linux
and Windows, using shared original Orbiter propagation code, and compare 601
samples against a frozen pre-refactor Windows reference.

**Milestone complete (2026-10-31).** All eight jobs passed in
[hosted acceptance run 41177834521](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41177834521),
testing commit `6f79da173ee016fa693966026d68bcf22831bb12`.
The four native Linux/GCC and Windows/MSVC x64 Debug/Release builds each passed
all eight CTest targets. Both full Windows application builds passed their
existing Lua/collision suites and frozen-reference verification. Native
cross-platform comparison and application Debug/Release comparison passed.

The original Windows prerequisite passed before extraction in
[run 41175652054](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41175652054).
Original traces and capture evidence remain frozen in [Reference](Reference/README.md).
Final reports, provenance, all eight CI artifacts and complete job logs are
preserved in [Verification](Verification/README.md), beyond hosted retention.

All parsed numerical samples agree exactly across the four native builds.
Their maximum error against the original Windows orbit/spin reference is
`1.1175870895385742e-7 m` in position and `8.866990313695243e-11 m/s` in velocity;
orientation, angular velocity and MJD differences are zero. Half-step position
error against its frozen reference is `1.2013700229374393e-7 m`.
Both refactored Windows applications reproduce all three original traces
numerically exactly. No tolerance was widened and no reference was regenerated.

## Local verification

Local Linux GCC 15.2/CMake 4.2.3 Debug and Release each pass all eight suites.
These local results are separate from the hosted acceptance matrix above.
Local orbit analytical position error is `1.4143184329290157e-6 m`; half-step
error falls to `1.1808439414391757e-7 m`. Energy/angular-momentum relative drift
stays below `7e-15`; free-spin angular error is below `5.1e-10 rad`.


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
CTest runs math, orbital elements, collision, VECTOR3 layout, trace I/O,
headless reference parity, headless error paths, and trace-tool validation.
Python is a test/capture dependency; the runner itself is native C++.

## Running a scenario

```sh
/tmp/orbiter-portable-release/orbiter-headless \
  --scenario "$PWD/Tests/Portable/Fixtures/TwoBody.scn" \
  --fixed-step 1 --steps 6000 --trace /tmp/orbit.csv
```

On Windows use the corresponding `orbiter-headless.exe` from a native MSVC x64
build (`-G Ninja` in an MSVC developer shell). No display server, graphics
libraries, Wine, Python runtime or downloaded visual assets are required to run
it. Paths work independently of the working directory. The scenario's directory
is a bundle containing `Orbiter.cfg`; its explicit relative `ConfigDir` locates
the system, primary and `Vessels/<class>.cfg` files. CLI step/count override the
profile's fixed step, allowing the supplementary half-step run.

Supported scenario fields are `BEGIN_ENVIRONMENT` (`System`, `Date MJD`), optional
`BEGIN_FOCUS` (`Ship`), and `BEGIN_SHIPS` with exactly one `name:class` vessel,
`STATUS Orbiting <primary>`, `RPOS`, `RVEL`, optional `AROT` and `VROT`, then
`END`. Orbiter's existing comment trimming and configuration-value parser are
shared with the application; fields are case-insensitive, semicolon comments
and Windows/Linux line endings are supported. Identifiers use ASCII letters,
numbers, underscores or hyphens. Use the supplied bundle as the supported
configuration schema. Unknown/duplicate fields and enabled unsupported physics
are rejected rather than silently ignored.

Only a fixed spherical primary and one unpowered generic vessel are supported.
Mass, radius, initial position/velocity, attitude, angular velocity and positive
principal inertia are loaded explicitly. There is no atmosphere, terrain,
collision response, radiation force, gravity-gradient torque, orbit stabilization,
Lua, vessel DLL loading, thrust, moving primary or Solar System ephemeris support.
The primary's velocity must be zero, aerodynamic cross sections zero, and the
profile must select RK4 with one substep. Nonfinite states, surface contact,
missing assets, invalid arguments and trace-write failures return nonzero.
A trace cannot overwrite an input file. `--help` documents CLI defaults.

## Shared numerical boundary

`orbiter_portable_core` reuses `Vecmat.cpp`, `Element.cpp`, `TimeData.cpp` and
`ConfigFile.cpp`. `PhysicsCore.h` holds the original point-mass gravity, full
Euler equation, RK4 stages, state finalization and compensated-increment flush.
The existing Windows application calls those same functions; its other force
models and propagators remain in the application. Stage expression order,
left-handed coordinate conventions and quaternion update are retained.
`ElementApplication.cpp` preserves legacy Windows constructors/methods as adapters
to explicit epoch/simulation-time inputs. The SDK's public `VECTOR3` layout is
unchanged. The session API is internal to `Src/Orbiter/Portable`.

The native session owns time/state and uses a deterministic zero initial flush
counter. The application retains its original randomized counter phase; this
can change final rounding below a micrometre. Acceptance is measured against
the unchanged frozen engine, with the original budgets below.


## Original Windows reference capture

The dedicated **Portable Core and Windows Reference** workflow builds the
portable tests with GCC/Linux and MSVC/Windows, x64 Debug and Release. Its manual
`verify_windows_application` input (default true) additionally builds the current
Windows application and existing tests, then compares its output with the frozen
original Windows traces. Native traces from all four jobs are also compared
against the frozen reference and each other. Logs, compiler settings, CSVs and
reports are archived for 14 days.

The original capture was performed before extraction using the historical
`capture_windows_reference` input at commit `1009ee22`. The guarded capture script
intentionally refuses the refactored sources. To reproduce that historical
capture, use a clean checkout of that commit.
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
python Tests/Portable/verify_windows_application.py `
  --source . --orbiter out/reference-app/Orbiter.exe `
  --output out/application-release-verification --configuration Release
```

Repeat from a separate Debug build and output directory. Build D3D9Client with
the original application because LuaInterpreter
unconditionally includes its generated `gcCoreAPI.h`. This is a build-time
requirement of the existing Windows test graph; reference runtimes do not load
a graphics-client plugin, and the native runner does not link graphics code.
For the verification script, preserve `configure.log`, `build.log`, `ctest.log`,
`compiler.txt`, and `build-metadata.txt` alongside `Orbiter.exe`; the workflow
records these automatically. The commands above show the build/test invocation;
use the workflow for the complete reproducible evidence collection. Hosted runs use the authorized public destination,
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
native runner does not need a DLL. No original numerical source is changed
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
fully finalized step, plus the final step when the count is not divisible by ten;
at the default run length there are 601 rows.

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

## Reference preservation and acceptance

The original capture passed its numerical/source gates before extraction and
was reviewed and committed in `874d6caa`. Its source commit remains
`1009ee2251931ec9e120047dc41d936c216b9ed0`. No automatic baseline refresh is
permitted. Reference SHA256 checks run before native and application parity tests.
The checked-in original evidence archives outlive hosted artifact expiration.

The completed acceptance gate required all four native x64 GCC/MSVC Debug/Release jobs,
comparison of every sampled state across platforms and with the frozen original,
and both full Windows application builds/existing tests/reference verifications.
Local Linux results alone would not satisfy this gate. Broader scenario compatibility
and a native graphical Linux application remain later milestones.
