# Accepted Windows cockpit and instrument reference

[Run 41458001638](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41458001638)
passes all nine reduced cases twice in MSVC x64 Debug and Release. These cover
all ten stock MFD modes, all three HUD modes, and the actual DG and DG-S 2D panels
and virtual cockpits, using production Sol and stock assets.

The application/SDK is fully rebuilt at
`f725194209634f7fd5d1d44d426cfa9b5e303e37`. Original Pane, HUD, MFD, panel and VC
code is unchanged. DG has one declared constructor initialization fixing an
indeterminate fuel-display sampling time. The failed original capture and exact
repair are documented in [the Phase 6 notes](../../../../Docs/Production/Cockpit.md).
Physics formulas, earlier references and acceptance budgets are unchanged.

The renderer/control-driver source is
`68400a7d3750240afb53890e1da2306c71f6380e`. Each process completes sixty original
quarter-second ticks. It records 61 finalized states and real drawing text,
HUD glyph geometry/atlas copies, MFD textures, loaded assets/DLLs and full
1280x720 readbacks at ticks 20 and 50. No image masks are used. Original MFD
wall-time limiting is respected by pacing, without replacing its scheduler.

Both complete Windows application builds pass all 22 existing tests. Within
each configuration, state/text/geometry/atlas traces repeat identically. The
Debug/Release comparison has zero numerical and projected-overlay differences,
identical displayed text and atlas updates, and image SSIM 1.0 for every case.
The downloaded artifact hashes and an independent local comparison agree with
the hosted results. Representative frames were visually inspected.

`provenance.json` pins original source/input hashes, all five original artifact
ZIPs, 1,712 canonical evidence-file hashes and the unmodified budgets. Large
captures, application/SDK binaries, real client/driver binaries, build metadata,
logs, shaders and notices belong in the
[versioned evidence release](https://github.com/dcajacob/orbiter-cross-platform/releases/tag/production-windows-cockpit-v1).
The preservation workflow verifies original bytes and never replaces a release.

```sh
python3 -B Tests/Production/Cockpit/frozen.py
python3 -B Tests/Production/Cockpit/frozen.py --cache out/cockpit-cache --output out/cockpit-frozen
# The same command with --offline uses only verified cached ZIPs.
```

Capture is manual-only after acceptance. There is no automatic refresh or
tolerance adjustment. The loader rejects failed captures, changed inputs,
changed archives, and an existing output directory.

This establishes the reference needed for native instrumentation extraction.
It does not establish native cockpit/DG functionality, interactive picking and
controls, all stock scenarios, or completion of Phase 6. The accepted laptop
preview remains the Phase 5 ShuttlePB/ISS external-view build.
