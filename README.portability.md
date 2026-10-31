# Cross-platform Orbiter engine bootstrap

The next implementation adds a [separate native graphical client](README.native.md).
Its local Linux hardware/software checks pass; hosted acceptance is pending.

**Milestone complete (2026-10-31): native headless Windows/Linux parity is
verified.** The command-line runner advances the supported unpowered vessel for
6,000 one-second steps and emits 601 finalized-state samples. All eight jobs in
[the hosted acceptance run](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41177834521)
passed: native GCC/MSVC x64 Debug/Release, both full Windows application builds
and existing tests, and both comparison jobs. The frozen pre-refactor reference
is unchanged. The native builds agree numerically exactly with each other and
within 0.12 micrometres of the original Windows reference across the tested cases.

See [the portable milestone instructions](Tests/Portable/README.md) for build/run
commands, supported inputs, trace contracts and results. Complete accepted CI
evidence is preserved in [Verification](Tests/Portable/Verification/README.md).
Graphics, general scenario support, atmosphere, terrain, collisions, Lua,
vessel modules and Solar System ephemerides remain outside this native milestone.
Earlier milestone notes below retain the installation/build history.

Local project on `dan-xps16`: `/home/dan/GIT/orbiter-cross-platform`.
Branch: `portability/native-core-bootstrap`.

## Baseline and scope

Official upstream: https://github.com/orbitersim/orbiter
Baseline: `8e6ae437901417eef56f08b8f969ff92df83db5e` (cloned 2026-10-30).
Publication destination: https://github.com/dcajacob/orbiter-cross-platform
Full upstream history, README and MIT LICENSE are retained in this portability
project. Existing `/home/dan/GIT/orbiter`
binary installation is separate and untouched.

Goal: preserve Orbiter physics, vessel and scenario behavior while separating
simulation, platform services, and graphics/UI. Linux and Windows should share
one engine. The first native runner now covers the fixed-primary milestone.

## First achieved milestone

The existing `Src/Orbiter/Vecmat.cpp` compiles and its basic numerical tests run
natively under Ubuntu GCC 15.2 / C++17, without Windows headers or libraries.
Baseline compilation failed because both `qrdcmp` friend declarations specified
default arguments. Defaults now live on namespace declarations; both three- and
four-argument call forms remain available. No numerical implementation changed.

Run from the repository root (no downloads or CMake required):

```sh
g++ -std=c++17 -O2 -I Src/Orbiter Tests/Portable/Vecmat.Portability.cpp Src/Orbiter/Vecmat.cpp -o /tmp/orbiter-vecmat-portability
/tmp/orbiter-vecmat-portability
```

Passed: dense 3x3 and 4x4 QR systems with analytically constructed solutions,
explicit/default singular-pointer call forms, zero-matrix singular flags,
vector normalization and identity transformation. Finite numerical values must
meet absolute tolerance `1e-12`. This is a small regression suite, not a complete
validation of Vecmat, integrator accuracy, or cross-platform simulation parity.
`git diff --check` also passed.

Optional standalone CMake route (CMake >=3.19):

```sh
cmake -S Tests/Portable -B /tmp/orbiter-portable-build
cmake --build /tmp/orbiter-portable-build
ctest --test-dir /tmp/orbiter-portable-build --output-on-failure
```

At this first milestone CMake was absent, so that route and the main upstream
CMake build had not been run. The standalone route was subsequently verified below. Windows compilation/testing has not been performed. No packages
were installed. Upstream integration/Lua suites were not run. The collision suite was subsequently
run successfully; see the second milestone below.

## Dependency map from inspected source

| Boundary | Evidence | Incremental work |
| --- | --- | --- |
| Build | Root CMake adds `/MP` for non-Ninja generators and defaults D3D9 on; Src/Orbiter links Windows libs | Introduce an opt-in portable component build before attempting the app |
| UI/input | Src/Orbiter common sources include Launchpad, dialogs, Input, Win32 ImGui backend even with NOGRAPHICS | Separate application/UI lifetime from simulation lifetime |
| SDK/ABI | Orbitersdk/include/OrbiterAPI.h includes windows.h; ModuleAPI exposes Windows handles | Identify portable data types and retain Windows compatibility adapters |
| Math | Vecmat.cpp has no Windows dependency; two declaration errors blocked GCC | Compile original code directly, add numerical regression coverage |
| Collision | CollisionCore.h includes OrbiterAPI.h for VECTOR3 | Extract minimal shared data types carefully, then reuse existing Collision.CollisionCore tests |
| Orbital elements | Element.cpp includes Orbiter.h, Config.h, windows.h and uses global TimeData | Separate configuration/time inputs from orbital calculation without stubbing them |
| Existing tests | Tests/CMakeLists.txt ties Lua tests to Orbiter and SDK; has a self-contained collision helper | Reuse existing tests as boundaries are made portable |

The independent portable test directory intentionally avoids changing the main
Windows build. Integrate it into shared CI once Windows execution is available.

## Existing Linux work reviewed

Fetched https://github.com/TheGondos/orbiter branch `linux` for read-only
comparison, commit `ad96494482e6101afebf1c635e4e1f542623b51d` (2024-05-17).
Its Vecmat.h removes the friend defaults too, and its top-level build uses GLFW
and other native dependencies. It also changes math types (including glm::dvec4),
so this bootstrap does not import that wider rewrite. No reference code was
copied. The fetched commit remains available locally via its hash; both named remotes
point to official upstream.

## Next milestones and acceptance gates

1. Make the shared collision data types independent of Windows and run the
   existing collision regression suite natively; keep public layout/ABI stable.
2. Isolate orbital-element computation from configuration and global time,
   first adding reference fixtures from the unchanged Windows implementation.
3. Define explicit simulation stepping, time, asset and module-loading interfaces.
   Inventory actual dependencies before fixing a new interface contract.
4. Run one deterministic, fixed-step scenario through the original propagation
   code on Windows and Linux: same initial state, timestep, force model, assets
   and output sampling. Record position, velocity, attitude and simulation time.
   Specify per-quantity absolute and relative tolerances from Windows reference
   runs and numerical error analysis before declaring parity. The math test's
   `1e-12` tolerance must not be reused blindly for scenario state.
5. Attach native UI/graphics clients after the simulation boundary is validated.

Initial setup need (now resolved): install CMake through the user's normal
package-management workflow. Windows CI or a
Windows development host is needed to substantiate Windows compatibility.

## Maintaining the upstream connection

`upstream` names the official https://github.com/orbitersim/orbiter repository;
its default branch is `main`. `origin` is the public publishing destination,
https://github.com/dcajacob/orbiter-cross-platform. Use `upstream` for
future reads and integration. The complete Git ancestry is retained, with the
initial baseline recorded above. Our work stays on `portability/native-core-bootstrap`.

Prefer small reviewable commits, additive platform boundaries, and existing
source paths. Avoid mass formatting, renaming, or vendored copies of core code.
Where appropriate, prepare generic fixes for potential upstream contribution,
but submission requires separate instruction.

Repeatable integration workflow, performed deliberately rather than automatically:

1. Review and commit current local changes before integration. Do not run a merge
   over the currently uncommitted bootstrap work. Confirm `git status --short`
   is empty, and run the currently available tests to establish a baseline.
2. `git fetch upstream` updates remote-tracking refs without changing our files.
3. Review `git log --oneline HEAD..upstream/main` and
   `git diff HEAD...upstream/main`, including build and API changes.
   Record `git rev-parse upstream/main` as the proposed integration commit.
4. Create a temporary integration branch from the portability branch, for example
   `git switch -c integration/upstream-YYYY-MM-DD` (choose a fresh name).
5. `git merge --no-ff --no-commit upstream/main` stages a reviewable integration.
   Resolve conflicts by preserving intended upstream behavior and the portable
   boundary; never blanket-select ours/theirs. If the approach is unclear,
   stop and inspect callers/tests. `git merge --abort` returns to the clean
   pre-merge state if this integration attempt must be abandoned.
6. Inspect the combined diff and run the gates below. Commit the integration only
   after reviewing results, recording the fetched SHA, conflicts and validation.
   Move the portability branch forward with `git merge --ff-only` from the tested
   integration branch when all required gates are met. Do not push as part of this
   workflow unless separately authorized.

Required gates evolve with the project:

- Now: GCC C++17 native math checks and `git diff --check`. The standalone CMake
  route also needs execution once CMake is installed.
- Before treating an integration as Windows-compatible: configure/build with the
  supported Windows toolchain and run upstream unit and scenario tests. Preserve
  existing Windows API behavior and default-argument call compatibility.
- As portable components are added: run their original regression suites on both
  systems; include collision tests after the SDK type boundary is extracted.
- Once a headless runner exists: compare fixed-step scenario traces on Windows
  and Linux against explicit per-quantity tolerances and inspect deviations.

CI should run Windows and Linux gates on proposed integrations before advancing
our working branch. This is a policy/plan, not an installed CI configuration:
Windows and full scenario gates are currently unavailable. Missing gates must
be reported, not marked passing. Upstream changes can require manual conflict
resolution or architectural work; no conflict-free or automatic merge guarantee
is implied. Keep the original baseline immutable in these notes, and append each
successfully validated integration SHA and test evidence to an integration log.

## Second milestone: native collision regression suite

Extracted the existing `VECTOR3` typedef verbatim into
`Orbitersdk/include/OrbiterVector.h`. OrbiterAPI.h includes that header, preserving
SDK consumers' access to the same type; CollisionCore.h includes only that small
header. Collision algorithms and upstream test cases are unchanged. The SDK's
existing recursive header copy/install rules include the new header.

Native GCC results on 2026-10-30:

- Original collision suite: **132610 assertions passed in 15 test cases**, including
  random oriented-box comparisons against an independent separating-axis test,
  penetration depth/contact checks, degenerate shapes and planetary translations.
- New VECTOR3 compile-time layout checks passed (size, alignment, component
  offsets, standard layout, trivial copyability, repeat inclusion).
- Existing bootstrap math suite passed; `git diff --check` passed.

This confirms these components on Linux, not the whole simulator or Windows ABI
compatibility. The moved declaration retains its anonymous struct extension,
which GCC and MSVC support; this is not a claim of strict ISO portability.
Windows must still compile SDK consumers and run both suites.

Build tools: `build-essential` was already installed, version
`12.12ubuntu2.26.04.2`. Installing CMake with approved escalation was attempted,
but `sudo` failed because the session has the `no new privileges` flag set.
No apt packages were changed. Run in a normal host terminal:

```sh
sudo apt-get install cmake
```

Then run the standalone CMake build including the original collision suite:

```sh
cmake -S Tests/Portable -B /tmp/orbiter-portable-build -DORBITER_PORTABLE_COLLISION_TESTS=ON
cmake --build /tmp/orbiter-portable-build -j2
ctest --test-dir /tmp/orbiter-portable-build --output-on-failure
```

At this second milestone the CMake route was still untested; it was subsequently
verified in the final section below. It fetches the same official Catch2
preview used upstream, pinned to commit
`b9853b4b356b83bb580c746c3a1f11101f9af54f` (`v3.0.0-preview3`). Its optional POSIX
crash handler is disabled on Linux because the preview assumes MINSIGSTKSZ is
constant, which fails with modern glibc. Test assertions remain enabled; fatal
signals still fail the process but lack Catch2's custom report.

The passing direct compiler run used that exact Catch2 release's amalgamation
and a temporary include adapter, leaving the upstream tests unmodified:

```sh
# One-time dependency fetch (already present under /tmp on this laptop):
git clone --depth 1 --branch v3.0.0-preview3 https://github.com/catchorg/Catch2.git /tmp/orbiter-catch2-preview3
# Verify its HEAD equals the pinned SHA above before building.
git -C /tmp/orbiter-catch2-preview3 rev-parse HEAD
mkdir -p /tmp/orbiter-catch-include/catch2
printf '#include "catch_amalgamated.hpp"\n' > /tmp/orbiter-catch-include/catch2/catch_all.hpp
g++ -std=c++17 -O0 -DCATCH_CONFIG_NO_POSIX_SIGNALS -I Src/Orbiter -I Orbitersdk/include -I /tmp/orbiter-catch-include -I /tmp/orbiter-catch2-preview3/extras Tests/Collision.CollisionCore.cpp Src/Orbiter/CollisionCore.cpp Src/Orbiter/Vecmat.cpp /tmp/orbiter-catch2-preview3/extras/catch_amalgamated.cpp -o /tmp/orbiter-collision-tests
/tmp/orbiter-collision-tests
g++ -std=c++17 -I Orbitersdk/include Tests/Portable/Vector.Layout.cpp -o /tmp/orbiter-vector-layout
/tmp/orbiter-vector-layout
```

Next: execute the CMake route after host installation and obtain Windows test
coverage before advancing to orbital-element/global-time separation. No upstream
integration, public push, package-source change or system-security change occurred.

## CMake verification completed (2026-10-30)

The user installed CMake from the normal host terminal. Verified installed:
CMake `4.2.3` (Ubuntu package `4.2.3-2ubuntu2`), build-essential
`12.12ubuntu2.26.04.2`, GCC `15.2.0`. The earlier installation blocker is resolved.

Exact successful commands, from the repository root:

```sh
cmake -S Tests/Portable -B /tmp/orbiter-portable-build -DORBITER_PORTABLE_COLLISION_TESTS=ON -DFETCHCONTENT_SOURCE_DIR_CATCH2=/tmp/orbiter-catch2-preview3
cmake --build /tmp/orbiter-portable-build -j2
ctest --test-dir /tmp/orbiter-portable-build --output-on-failure
```

The source override reuses the previously downloaded official Catch2 checkout;
its HEAD was verified as `b9853b4b356b83bb580c746c3a1f11101f9af54f`.
The automatic network-fetch route without that override was not exercised.

Result: **3/3 CTest tests passed**, zero failures (0.25 seconds test execution).
`Collision.Portability` reports **132610 assertions in 15 test cases**;
`Vecmat.Portability` passes the numerical checks and `Vector.Layout` passes its
compile-time assertions. Final `git diff --check` passed.

The first split-source Catch2 build exposed a missing `<cstdint>` include that
was masked in its amalgamation. The standalone target supplies that include for
GNU/Clang, without modifying downloaded dependency sources. Together with the
Linux crash-handler setting documented above, both workarounds are scoped to the
standalone tests; upstream application/Windows CMake files remain untouched.
A nonfatal CMake warning remains about the preview's old minimum CMake version.

Local evidence: `/tmp/orbiter-portable-build.log` and
`/tmp/orbiter-portable-build/Testing/Temporary/LastTest.log` (temporary artifacts).
All project edits remain uncommitted on `portability/native-core-bootstrap`.
No push or upstream merge was performed. Windows tests, the full application
build, and a native headless scenario remain outstanding. Next gate: verify the
portable targets on Windows, then isolate orbital-element time/configuration
inputs and define a fixed-step reference scenario.

## Headless parity milestone: reference preparation (2026-10-30)

Accepted goal: one unpowered vessel around one fixed spherical primary for
6,000 one-second steps, with 601 samples matching a frozen original Windows
reference on native Linux and Windows. Graphics, custom vessel DLLs, Lua,
atmospheres, terrain, collisions and Solar System ephemerides remain outside
this milestone.

Added an opt-in observer in the original Windows application, a portable trace
writer, the two-body scenario/configuration fixture, numerical trace validation,
and a Windows-only candidate-capture script with provenance and no automatic
baseline replacement. A dedicated workflow prepares x64 GCC/Linux and
MSVC/Windows Debug/Release testing, plus manual original-application builds,
tests, reference capture and Debug/Release comparisons. Existing workflows are
unchanged. The Windows loader needs a test-only static-primary provider; its
purpose and the primary's global translation are documented in the portable
instructions. Gravity and propagation sources remain identical to upstream.

Local evidence from this implementation:

- Clean GCC 15.2 Release build, including a fresh download of the pinned Catch2:
  original **3/3** bootstrap targets passed before observation changes.
- Extended suite: **5/5** CTest targets pass in separate Release and Debug builds.
  Trace validation includes 17 Python test cases using explicitly synthetic
  validator inputs; these are not engine references.
- Original collision suite still reports **132610 assertions in 15 test cases**.
- Workflow YAML parsed and its trigger, permission and build-matrix structure
  checked locally; no hosted execution has occurred.

Local build directories: `/tmp/orbiter-bootstrap-clean` (Release) and
`/tmp/orbiter-bootstrap-debug` (Debug). Each contains CMake settings and
`Testing/Temporary/LastTest.log`; the Debug build log is
`/tmp/orbiter-bootstrap-debug-build.log`. All are temporary evidence.

The Windows application observer/provider have not been compiled or executed on
this Linux host. No frozen reference exists. Consequently the orbital-element
refactor, shared propagation/session boundary and native headless runner have
not started: the accepted plan explicitly requires hosted Windows capture
before those changes. The authorized public publishing destination is now
https://github.com/dcajacob/orbiter-cross-platform; official upstream is retained
separately. Windows reference execution remains pending publication of this
prepared code. No physics extraction or upstream integration has occurred.

## Public hosting and hosted bootstrap verification (2026-10-31)

Published https://github.com/dcajacob/orbiter-cross-platform with full upstream
ancestry retained. `main` and `portability/native-core-bootstrap` initially point
to `c2ce0f61db2cbac58e7281a87787c3faa2eaf365`; implementation commit
`07936328` contains the prepared portable tests and original-app observer.
The new repository's empty setup history was joined without force-pushing or
changing upstream history. `origin` uses the user's authenticated GitHub SSH
connection; `upstream` still identifies official Orbiter.

Hosted run: https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41175171274

All four portable jobs passed: Ubuntu 24.04/GCC and Windows 2022/MSVC, x64 Debug
and Release, **5/5 CTest targets per job**. Automatic Catch2 download was exercised
successfully. The Windows Release collision suite reports **132535 assertions
in 15 test cases**; assertion counts can differ from Linux because some checks
depend on generated geometry. All cases pass on both platforms.

The original Windows Debug/Release application builds and reference-capture
jobs exposed an existing build dependency: LuaInterpreter unconditionally
includes the D3D9Client-generated `gcCoreAPI.h`. The reference workflow now retains
the upstream D3D9Client build setting; isolated reference runtimes do not load a
graphics client. The application/reference jobs must be rerun with that setting.
No reference has been frozen and no
physics extraction has started. The original numerical-source hash check passes
for all 13 recorded source files.

With explicit user approval, the inherited **Nightly** and **Artifact Cleanup**
workflows were disabled through repository settings. Their source files remain
unchanged; validation artifacts retain the dedicated workflow's 14-day policy.
The temporary manual history-import workflow was removed after GitHub's
restricted job token could not publish inherited workflow files. Publication
completed directly over SSH instead; no publishing automation remains installed.

## Original Windows reference accepted (2026-10-31)

Corrected hosted run:
https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41175652054
Capture source commit: `1009ee2251931ec9e120047dc41d936c216b9ed0`.
All seven jobs passed: four portable builds, two full Windows application builds
with existing tests and reference capture, and Debug/Release trace comparison.

Reviewed and frozen under `Tests/Portable/Reference`: orbit, free-spin and
half-step traces, provenance and complete build/capture evidence archives.
Default traces have 601 samples; the half-step trace has 1201 samples over the
same 6000-second duration. Debug and Release samples agree numerically exactly,
and same-executable repeats agree byte-for-byte.

Maximum circular-orbit position error is `1.3123027900649334e-6 m`; half-step
position error falls to `1.2411773373862428e-7 m`. Free-spin angular error is
`4.999946986498749e-10 rad`; energy and angular-momentum relative errors stay
below `7e-15`. No acceptance budget was changed. Artifact SHA256 digests and
source/fixture content were checked locally before freezing the reference.
The Windows baseline prerequisite is now satisfied; shared-core extraction and
the native headless runner may proceed.

## Native headless milestone accepted (2026-10-31)

Implementation stages are preserved as reviewable commits: original-reference
acceptance `874d6caa`, explicit orbital calculations `3e1d0c8e`, shared propagation
`59c1a2d7`, runner/parity checks `f4f3fce2`, exact reference checkout bytes
`6b05f1cb`, and explicit application-service includes `6f79da17`.

Final hosted run:
https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41177834521
Tested source: `6f79da173ee016fa693966026d68bcf22831bb12`.
Each native build passed 8/8 suites; each full application passed 2/2 existing
suites plus orbit/repeat/half-step/spin verification. All parsed native samples
agree exactly across platforms and build modes. Both current Windows application
builds reproduce the frozen original samples numerically exactly. Full reports,
compiler settings, effective inputs, traces, build/test logs and complete CI job
logs are checked in under `Tests/Portable/Verification` with SHA256 digests.

Local Linux Debug/Release also passed 8/8 suites. These are recorded separately
from hosted results. The runner links only the native C++ runtime and standard
system libraries; it runs without a display server, Wine, graphics or visual assets.
The public SDK and `VECTOR3` layout are preserved. The full native graphical
application and broader physics/scenario compatibility remain future work.
