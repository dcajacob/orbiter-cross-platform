# Heading-marker lifetime regression

`heading_tape_test.py` compiles the actual `HUD::AddMesh_HeadingTape` method from
`Src/Orbiter/hud.cpp` against CPU mesh storage. ASan, UBSan and LSan run without
suppressions. The 24 marker cases cover left, right, in-range and wrapped
headings, index bounds and appending after existing vertices. A separate case
disables the marker. This checks the production method without requiring a
display; full scenario rendering is a separate integration check.

```sh
python3 -B Tests/Production/Cockpit/heading_tape_test.py \
  --output out/heading-check
```

Run outside a ptrace sandbox for LeakSanitizer, with GCC or Clang available as
`CXX` (default `c++`). `--source PATH` can exercise a prior source revision in
a new output directory. The pre-fix method fails with stack-use-after-scope.
Each marker branch previously stored pointers to arrays that expired before
the mesh write. The repaired method performs that same write within the
branch. `cockpit_source.py` verifies every original value and mesh-write
expression after this explicit lifetime move.

The real Geostationary orbit scenario also reproduces the error before the fix
and completes 60 sanitizer frames afterward. The full 38-scenario stock census
then completes all 2,280 presentations and teardown without sanitizer errors.
Its strict runner still rejects GeneralApiTest's original Lua assertion.
[Local evidence](../../../Docs/Production/HudHeadingVerification.json)
