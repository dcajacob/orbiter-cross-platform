# Tracking-camera preset save compatibility

An actual Release/SSE2 native stock writer at `f82b7392`, collected by
`f3e86add`, completed 960 steps and saved the unchanged `2024 Edition/Space Shuttle ascent autopilot.scn` scene.
The independent early comparison with its preserved same-profile Windows
writer found three differing tracking-preset target tokens: `STS-101%`, `ISS%`
and `Earth%` instead of the Windows names without the trailing percent.

`CameraMode_Track::Store` inherits the invalid conversion `%:` in its format
string. The Windows CRT drops that percent; glibc writes it. Replacing only
`%s%:` with `%s:` gives the established Windows serialization on both systems.
The source audit restores exactly this literal before conserving the complete
original camera implementation. No reference, precision or comparison budget
changes.

The permanent [serializer regression](../../Tests/Production/CameraPreset/Store.Test.py)
passes 18 exact-format cases and four damaged-source controls locally. The full
622-file extraction/source-conservation audit also passes. The actual method also passes the MSVC control run, where the old Windows writer
and repaired writer produce identical output. Complete all38 runtime parity
remains open.

Local evidence stays in the original checkout under:

- `out/phase6-current-native38-early-Windows-pair-v1.json`: actual failed comparison.
- `out/phase6-current-native38-Release-sse2-stock-writer-v3/remaining_stock_002-1`: completed native run and saved scenario.
- `out/phase6-recovered-Windows-observations-f3d-v1/decoded-for-native-qualification-v1/Release-sse2/remaining-stock-repaired/remaining_stock_002-1`: preserved Windows writer.
- `out/phase6-camera-preset-format-controls-v1`: actual compiled-method positives and rejected mutations.
- `out/phase6-current-native38-v3-interruption-v1.json`: four precisely identified interrupted candidate campaigns and process trees.

The incomplete collections retain their raw files and earn no complete-matrix
qualification. The earlier successful PoweredUp staging canary and its
independent audit remain separately scoped. Phase 6 and class admission remain
incomplete.

Fresh ASan/UBSan packages from `2d6fa396` now complete the unchanged ascent-
autopilot mission twice in all four profiles, both as stock writers and after
loading the exact hashed Windows save. All sixteen actual native processes
complete 15,360 presentations, clean context destruction and unsuppressed
sanitizers. Independent comparisons pass original physical, camera and full-
frame budgets, SSIM 1.0, identical actual clocks and complete parsed saved
content, excluding only protocol-declared operator descriptions. The
[runtime verification record](CameraPresetRuntimeVerification.json) pins the
three independent audits and their exact scope.

The subsequent full38 attempt stopped on a separate playback/save-boundary
mismatch in `2024 Edition/Space Shuttle to ISS.scn`. Its recorded physical state
and camera match exactly and SSIM is 1.0; Leonardo's saved landed-coordinate
cache differs. That failure remains retained and the complete matrix remains
unqualified. These sixteen successful runs do not replace the full matrix.
