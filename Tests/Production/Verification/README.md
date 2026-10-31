# Production bootstrap evidence

Accepted **Windows window/WGL bootstrap**, not an Orbiter graphics-client run:
[run 41185963598](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41185963598),
source `92f33c72f9a5b598cd25eacd87bb83c920ad969c`.

Both MSVC x64 Debug and Release execute the real Win32/WGL probe successfully.
Each performs three window/context create/render/present/resize/shutdown cycles,
compiles GLSL, renders/readbacks a texture-backed FBO and checks every pixel.
The loaded-driver audit passes with application-local Mesa 26.2.6,
`llvmpipe (LLVM 23.1.4, 256 bits)`, OpenGL 4.6 core. The actual compiler is
MSVC 19.44.35229. Full runner/build metadata, DLL paths/hashes, license files,
console logs and raw RGBA readbacks are preserved in the original artifacts.

| Artifact | SHA256 of original ZIP |
| --- | --- |
| [Debug](Evidence/41185963598-production-wgl-Debug-x64.zip) | `66278ef6b48aebdfefd7a237f48ad7763459f61ac74e6d1c154774c5e3b92706` |
| [Release](Evidence/41185963598-production-wgl-Release-x64.zip) | `3bfe682d1867e1c5aa0e352130afe1a31b871651b135e78600d87ac69d2e3ebf` |

Downloaded bytes were checked against GitHub's recorded artifact digests. These
small evidence archives remain in Git beyond hosted retention; no Mesa binaries
or stock data package are committed. The complete runtime package/license lock
is recorded separately.

Production orbit/propulsion references are now [accepted and frozen](../Reference/README.md)
from [run 41187217665](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41187217665),
source `e70041fa2991d1bfefe66575ced1e32c92898f82`. Both Debug/Release original
application builds and existing tests pass, including original two-body parity.
Both production cases repeat byte-identically; cross-configuration position,
velocity, rotation, angular velocity, MJD, mass and fuel differences are zero.
The original Debug/Release artifacts and comparison ZIPs are retained in Evidence,
with individual ZIP/member digests in the accepted reference provenance.

Atmosphere/contact/docking/autopilot, pause/warp, object/focus lifetime,
persistence and vessel callback references are still required before extracting
their respective production subsystems. No fixture capture here establishes
stock corpus or graphical client acceptance.

The first production attempt,
[run 41186215473](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41186215473),
is **failed, not accepted**: the harness looked for `CurrentState.scn` instead of
Orbiter's `(Current state).scn`. Both builds and existing tests passed; the first
6,000-second Sol/ISS/ShuttlePB capture completed. Local inspection with the
corrected validator confirms 601 samples for each of five real objects, 30,006
driver/control events, actual ISS/PB meshes and exact Debug/Release agreement
for this first orbit case. Repeats and controlled cases were not run, so these
outputs cannot be accepted as a reference. The two original failure artifacts
are retained in `Evidence/41186215473-production-reference-*-x64.zip`, with
GitHub digests `904b62eb06fd03d3da0aaaf776313163c23353fff80897e694fc11afebcbbdc7`
(Debug) and `5a70b8c16a8edc458fb1bc3815ea776db00c680ab8601d93b72e2e501f5e4864`
(Release).

Native SPICE data coverage passed separately in
[run 41187217756](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41187217756).
Ubuntu 24.04/GCC 13.3 and local GCC 15.2/CSPICE N0067 pass 11,481 queries covering
41 Sol bodies and barycentres across 129 distinct epochs, plus rejection of an
unsupported epoch. The output SHA256 is identical between the two Linux builds.
This directly exercises the pinned CSPICE kernels; it is not production Orbiter
execution or full scenario initialization. The original
[coverage artifact](Evidence/41187217756-native-spice-data-coverage.zip) has SHA256
`43a0c4c2b4ff6d82585e3db3f435ced43ccaad3955b3b73e064b66ec390efec0`.
[LocalSpiceCoverage.json](LocalSpiceCoverage.json) retains the separate local result.

Standard planetary archives are locked separately from the orbital fixture data.
The publisher's Orbiter2016.zip SHA256 is
`bdbf747dd930ced34a3cca34b69dc7e2d9733e0b9498ee8d6224090cf008dc30`;
28 selected archive file hashes matched an existing compatible Orbiter-2024 data
directory locally. This input-resource result does not establish renderer or
terrain/contact acceptance, and does not change the frozen orbit data profile.

Final immutable-reference verification also passed in
[run 41189526342](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41189526342),
testing `e7d1fdec`. Both current Windows configurations match the accepted baseline
and each other's outputs. All 32 current trace/state/event/identity files are
byte-identical to their accepted counterparts. The
[verification evidence](Evidence/41189526342-verification.zip) preserves all six
production job logs and current build/SDK/dependency metadata, invocations,
saved scenarios and verification/comparison reports. Its manifest records the
original GitHub artifact hashes and explicit references to the already preserved
identical files, avoiding duplicate numerical traces in Git.
Verification evidence ZIP SHA256:
`f2280180a740bfd659d3cd07d05798e1fa8488ba899a9c34735a82151f610741`.

The existing [portable matrix](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41189526198)
and [native data audit](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41189526236)
also pass on the same tested source. Locally, the nine display-independent
portable suites, standard-data offline verification, frozen archive integrity,
budget-tampering rejection and numerical comparator negative checks pass.
