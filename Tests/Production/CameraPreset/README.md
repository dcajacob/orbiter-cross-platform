# Tracking-camera preset serialization

The inherited `CameraMode_Track::Store` format contains `%s%:`. The Windows CRT
writes the intended colon, while glibc retains an extra percent. A real native
960-frame `2024 Edition/Space Shuttle ascent autopilot.scn` save therefore writes `STS-101%`, `ISS%` and
`Earth%` in tracking presets, differing from the preserved Windows save.

The shared writer now uses the valid `%s:` format. Field order, precision,
mode names, references and all camera calculations remain unchanged. The camera
source-conservation audit permits exactly this literal repair and compares the
rest of the original implementation unchanged.

`Store.Test.py` compiles the actual production method with format warnings as
errors. It checks exact Windows-format output for all six tracking modes with
null, ordinary and percent-bearing target names (18 cases), and rejects four
damaged writers. It supports both a native C++ compiler and MSVC (`--msvc`).

```sh
python3 -B Tests/Production/CameraPreset/Store.Test.py --output out/camera-preset-store
python3 -B Tests/Production/extraction_source.py
```

These controls verify serialization. Fresh complete Windows/native writer,
exact-save reload, state/camera/frame, lifetime and admission gates remain
required. Frozen references and numerical/image budgets are unchanged.
