# Native legacy ISS and Module1 verification

The four unchanged legacy station scenes pass their scoped native parity gates.
Phase 6 remains incomplete. The tested runtime source is
`aeee5826eb86c5c64e6c0fc97f40a20f8104459e`; the preserved Windows application,
SDK and client remain at `f725194209634f7fd5d1d44d426cfa9b5e303e37`.

The corrected reference uses the original scenario entry points, Windows-native
launch separators, all 22 rescue recording files and actual per-vessel SDK
playback flags. Thirty-two original runs and forty native runs cover every
vessel and docking port at 61 finalized ticks per run. Each run contains 60
quarter-second frames, or 15 simulated seconds; this is not an entire nine-minute
rescue tutorial. All four Debug/Release automatic/SSE2 profiles and the additional
Debug ASAN/UBSAN profile pass the unchanged state, camera, landmark and complete-
frame budgets. Every full-frame SSIM is 1.0. Position, velocity, camera and
projected-landmark errors are zero; the largest rotation and angular-rate errors
are approximately 3.14e-16 radians and 8.11e-16 radians/second.

The docked dumbbell exposed a teardown use-after-free. `ClearDockDefinitions`
now retains port storage until all undock callbacks and NAV notifications finish,
preserving their original order. Missing-module rejection then exposed 676 bytes
of constructor-default allocations whose destructor could not run. The native
loader now reclaims those allocations on failure. Both normal and instrumented
packages reject all sixteen invalid factory, clone, capability and port cases
with zero presentations and clean graphics teardown. Leak detection remains
active without suppressions. Successful pre/post sessions retain byte-identical
state, docking data, playback flags, camera and full frames. The source audit
conserves all 479 owning files and Windows SDK layouts.

The independent original audit binds every extracted file to all four downloaded
ZIPs, rechecks the unchanged SDK/client against independently retained packages,
and verifies actual MSVC configuration, CRT linkage, math and loaded modules.
Twelve damaged captures and five playback/input controls pass per original
profile. Eight additional archive/source/build/launch/math/module identity
controls pass. An independent offline replay passes, and a same-size corrupted
archive fails before producing an audit. See the exact hashes and paths in
[the verification record](LegacyStationsVerification.json) and
[the v2 pins](../../Tests/Production/LegacyStations/observations-v2.lock.json).

Version 1 remains preserved with its documented rescue-playback limitation;
none of its archive identities or its observer tag moved. Version 2 uses the
separate `phase6-legacy-stations-original-v2` tag at the audited producer. [Public v2
publication](https://github.com/dcajacob/orbiter-cross-platform/releases/tag/phase6-legacy-stations-original-v2)
and a fresh anonymous four-archive replay both pass. The complete legacy evidence
archive retains five native packages/captures, all four original ZIPs, sources,
controls and failed-attempt context: 3,822 individually rehashed members,
463,788,960 bytes, SHA-256
`324fe385e45d14b8e6c8b10ed180697a0f5de743cf73c9c0622a6be50261a780`.
It is a verified local evidence archive; the four original ZIPs are also publicly
preserved. No font or stock-data collections are bundled.

The last complete pre-admission 157-scenario sweep remains 114 passes and 43
failures. A new complete sweep is required before changing that count. Current
hosted comparisons, remaining stock modules/assertion, interactive acceptance,
final hardware performance/input, the unavailable physical controller and full
Phase 6 evidence preservation remain open.
