# Original Windows Lua and AAP reference v1

The accepted reference is the Windows 2025 pair in
[run 41590681453](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41590681453),
produced at `739fdf943cf63dc4e05647cf64b0cde0ace22195`. It uses the preserved
original application/SDK/Lua libraries from `f7251942`, the original OpenGL
client and stock scripts, plus the recorded observation plugin.

All five cases ran twice in each Debug/Release build with default FMA3 and
forced SSE2 profiles. Both cross-build comparisons pass with exact Lua events
and controls, zero physical-state errors, and SSIM 1.0 for every compared frame
and MFD image. The archives contain the observer DLL, compile/runtime metadata,
provider identities, raw traces, images, and timing observations. The parent
cockpit reference preserves the original application and client binaries.

Qualification is scoped to the Windows 2025 CRT family. The matrix run's overall
conclusion is **failure** because its Windows 2022 default-profile comparison
still fails. Preservation checks all four pinned jobs: both complete captures,
the passing 2025 comparison, and the declared 2022 default comparison failure.
The three legacy artifacts and the complete workflow logs remain diagnostic
assets alongside the accepted pair. They are not substituted for the accepted
reference. The prior original-runtime frame-yield failure and controlled mutex
diagnostic remain documented in [the numerical evidence](../../../../Docs/Production/LuaHandoffVerification.json).

`provenance.json` fixes the accepted artifacts, every default/SSE2 capture file,
producer inputs, original runtime, clocks, cases and unchanged budgets. Automatic
refresh and replacement are forbidden. Verification reruns both original
comparisons before publication and after downloading public release storage.

```sh
python3 -B Tests/Production/additional_references.py lua \
  --cache out/original-lua-cache --output out/frozen-original-lua
```

`Debug/` and `Release/` contain the default-profile captures;
`diagnostic-sse2/Debug/` and `diagnostic-sse2/Release/` contain the baseline CPU
captures. `--offline` requires the three accepted ZIPs already in the cache.
Native simulator/image, stock-corpus, lifetime and hardware acceptance remain
separate Phase 6 requirements.
