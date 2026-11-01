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
| Production CPU Mesh/MeshManager and host resources | `57754800` | [41274799922](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41274799922) | [41274799926](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41274799926) | [41274799830](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41274799830) |
| Original State metadata with explicit epoch/path | `c14360ab` | [41275682190](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41275682190) | [41275682231](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41275682231) | [41275682252](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41275682252) |
| Mesh count/index validation before narrowing | `24591de6` | [41276717087](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41276717087) | [41276717080, attempt 2](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41276717080/attempts/2) | [41276717132](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41276717132) |
| Production Camera/PlanetarySystem ownership | `26f0bc37` | [41279054097](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41279054097) | [41279054051](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41279054051) | [41279054091](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41279054091) |
| Native module loader/bootstrap and actual shared Body fixture | `15867de9` | [41280064395](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41280064395) | [41280064421](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41280064421) | [41280064405](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41280064405) |
| Original Pines gravity and portable model loading | `c73d1477` | [41282440355](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41282440355) | [41282440315](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41282440315) | [41282440466](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41282440466) |
| Production CelestialBody and Windows module adapters | `c2813bf8` | [41284623399](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41284623399) | [41284623366](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41284623366) | [41284623362](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41284623362) |

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

The original four-platform portable evidence for source `c14360ab` is also
preserved in `Evidence/41275682252-portable-*.zip`, with GitHub artifact IDs,
SHA256s and source identity in `Evidence/portable-artifacts.json`. These ZIPs
contain configure/build/CTest logs, CMake caches and every sampled trace, including
the new scenario metadata manifest. Linux has 18 passing CTest entries and
Windows has 17; the additional Linux entry executes the existing POC renderer.
Its included POC images are regression evidence only, not production-client
evidence. The ZIPs contain no compiled binaries or asset packages.

`state-native-parity.json` records exact agreement for all 157 original scenario
environment/focus headers across the four hosted builds (metadata SHA256
`cf0740acab63ccf7cf34b9819b9227d27e5eeffbac14c070f721cd996f8bd5a0`).
The Windows client evidence ZIPs retain current scene traces, real loaded
driver audits, same-build application/SDK/dependency metadata and build/test logs.
`Evidence/windows-client-artifacts.json` records original artifact ZIP hashes and
every preserved member's hash. Current images are independently byte-identical
to the frozen PNG and its lossless RGBA decoding; their payloads are deduplicated
against that existing file, with exact hashes and a reconstruction recipe in the
manifest. No reference is modified. Compiled renderer modules are excluded. Both
Windows application metadata records identify the actual shared production DLL.

The integer-validation follow-up passes the same gates with identical numerical
and metadata comparison results. Its first Debug graphics attempt failed while
`tar` listed the digest-verified Mesa zlib package, before Orbiter execution.
The complete decoded failure log is retained as a gzip with hashes in
`graphics-setup-retry.json`. Attempt 2 passes using unchanged source and packages,
including actual Orbiter execution and the frozen image comparison. This setup
failure is not accepted as a graphics result and no tolerance is changed.

Local Linux verification is separate in `local-linux.json`: GCC 15.2 Debug/Release tests and the
production boundary under ASan/UBSan/LeakSanitizer pass. The native library is
built without a window, graphics libraries or downloaded assets. Its stock mesh
tests read tracked files. The existing installed two-body runner also executes
outside the checkout. These local results cannot replace hosted Windows gates.

Remaining Phase 3 requirements are tracked in
[EngineBoundary.md](../../../../Docs/Production/EngineBoundary.md).

Verify the preserved reports, archive/member hashes and lossless image
reconstruction without network access or reference changes:

```sh
python3 -B Tests/Production/Verification/EngineBoundary/verify.py
```

`module-local-linux.json` separately records 18 Debug and 19 Release checks,
nine standalone and sanitizer checks, C11 bootstrap-header compilation, and
rejection of an actual module from a separate engine/SDK build before
initialization. The matching module completes twenty production Body lifetimes.
This is an internal bootstrap fixture; native stock module interfaces and a
complete production world remain outstanding.

The Pines extraction also passes its separately frozen pre-extraction Windows
force reference: all 864 queries agree exactly across Windows/Linux Debug/Release
and each executable repeats byte-identically. The twelve independent J2 checks
pass. `pines-gravity-*.json` reports additionally compare standalone and full
application builds. The class/file tests cover all seven tracked coefficient
models and explicit parser/resource failures. These are direct force queries,
not native Solar System initialization.

The celestial extraction preserves all production state/callback and client
comparisons. Its actual class runs on Linux and Windows in controlled conic,
rotation, barycentre, interpolation, ephemeris/fallback-order and failure-cleanup
fixtures. Those callbacks are unit fixtures, not native stock SPICE modules.
The SDK audit conserves constants, atmospheric data, object/ephemeris flags and
all original Windows class declarations and implementations.
