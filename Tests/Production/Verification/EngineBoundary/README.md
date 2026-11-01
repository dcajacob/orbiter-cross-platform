# Partial production engine extraction verification

Phase 3 remains incomplete. This evidence verifies individual extractions;
it does not establish a Linux production world, native module SDK, graphical
Linux application or stock-playable release.

Each source below passes all three hosted gates: full Windows application and
original tests with frozen orbit/propulsion and fourteen behavioral cases;
current-application Windows OpenGL execution and frozen Phase 2 comparison;
and Linux GCC / Windows MSVC x64 Debug/Release portable checks.

| Component | Tested source | Production | Real Windows client | Portable |
| --- | --- | --- | --- | --- |
| Frame ordering and shared CPU parser | `f7861ec8` | [41238486267](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41238486267) | [41238486523](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41238486523) | [41238486499](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41238486499) |
| Production Body and shared math/time/configuration | `240b17a7` | [41239902123](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41239902123) | [41239902090](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41239902090) | [41239902155](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41239902155) |
| Production RigidBody and original propagators | `94d5267e` | [41272634399](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41272634399) | [41272634438](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41272634438) | [41272634393](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41272634393) |
| Verbatim SDK mesh value records | `a72fb8b8` | [41273799957](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41273799957) | [41273799955](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41273799955) | [41273799993](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41273799993) |

The preserved `*-client-comparison.json` reports show zero numerical and
projected-landmark differences and SSIM 1.0 both between configurations and
against the frozen original client. No image masks or changed budgets apply.
`rigid-native-parity.json` additionally compares 601 finalized samples from
each of ten original production propagators across four platform/configuration
builds. Maximum position disagreement is about 1.15e-10 m; all other compared
quantities agree exactly. The fixture is inertial/free-spin, not a Solar System.
The separate original two-body reference also passes unchanged.

`provenance.json` identifies full tested source revisions, hosted runs, original
comparison ZIP SHA256s and preserved report hashes. Downloaded ZIPs were checked
against GitHub's artifact digests before extracting these reports. Runtime
metadata, full traces and logs remain in the linked workflow artifacts; these
small reports are preserved here beyond artifact retention. They are verification
outputs, never replacement golden references.

Local Linux verification is separate: GCC 15.2 Debug/Release tests and the
production boundary under ASan/UBSan/LeakSanitizer pass. The native library is
built without a window, graphics libraries or downloaded assets. Its stock mesh
tests read tracked files. The existing installed two-body runner also executes
outside the checkout. These local results cannot replace hosted Windows gates.

Remaining Phase 3 requirements are tracked in
[EngineBoundary.md](../../../../Docs/Production/EngineBoundary.md).
