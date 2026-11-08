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
622-file extraction/source-conservation audit also passes. This is a writer
repair with focused validation; complete rebuilt runtime parity remains open.

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
