# Phase 6 desktop frame-time gate

`cases.json` fixes the benchmark before measurement: three unchanged stock
scenarios (landed exterior at Edwards AFB, geostationary 2D panel and Mojave VC),
two fresh-process repetitions on each desktop backend, 360 warmup frames and
1,800 measured frame intervals per run. Each frame executes one original
1/60-second physics tick. This bounded workload can perform more physics ticks
per wall-clock second than interactive 1x flight; it does not reduce the original
physics work per rendered frame. Original physics defaults are retained.

The medium profile uses the middle planetary patch-grid choice, 64 segments
(`PlanetPatchGrid=5`, supported powers 4/5/6), maximum surface level 18 and zero
resolution bias. Clouds, vessel shadows, night lights, water reflection, haze,
fog, specular reflection and particle streams remain enabled. `medium.cfg` and
the expected effective settings are hashed. Quality and budgets must not be
reduced after timing. The accepted 1280x720 Windows image gates remain separate.

The required framebuffer is 1920x1080. Native `WindowWidth` and `WindowHeight`
now express framebuffer pixels when explicitly configured. On Wayland, startup
converts to logical dimensions and settles actual surface-scale feedback before
constructing the original fixed-size cockpit. Fractional feedback may differ
from the output's integer scale. Blank buffer commits used for that negotiation
are recorded separately before scene creation. Default sessions without explicit
dimensions retain the established 1280x720 window policy. The independent 2x
engineering input fixture remains separate.

The driver requires the real desktop `wayland-0` or XWayland `:0`, the actual
Intel OpenGL renderer, effective medium settings, exact framebuffer dimensions,
complete visible/non-minimized frame records and normal context deletion. It
does not substitute Xvfb, a private compositor or llvmpipe. All scenario bytes
must match both the repository and staged assets. The native cockpit and MFD
mode traces must remain active throughout each internal view. Original 2D panel
draws are outside the existing per-object scene-mesh counter; the panel gate
checks loaded stock meshes and complete actual cockpit/MFD traces instead.
`cockpit-viewport.json` records the original `Pane::Width()` and `Height()`;
both must equal the measured framebuffer dimensions. Framebuffer size alone
cannot establish that the original cockpit was constructed at that size.

`frame-times.enabled` enables an observation-only renderer trace. It timestamps
entry to event polling, entry to `glfwSwapBuffers`, and return from that call.
The primary metric is **consecutive swap-return cadence**, including timing CSV
write overhead, application bookkeeping, polling, original physics, GUI,
rendering and swapping. This measures steady application throughput, not physical
display latency. It adds no GPU-finish barriers or replacement rendering path.
Poll-to-swap-return and swap duration are retained as diagnostics.

Every declared sample is retained, including outliers. Median must be at most
33 ms and nearest-rank p95 at most 50 ms in **every** run. The first measured
interval ends at frame 361 and begins at frame 360's swap return. No startup
time or warmup interval is silently included in, or trimmed from, that sample.
Power state and machine load are recorded; no governor, desktop, system driver
or power configuration is changed. Run the backends serially without another
benchmark or build competing for the GPU/CPU.

```sh
python3 -B Tests/Production/Performance/run.py \
  --backend wayland \
  --executable out/phase6-base-stations-engine/orbiter-production \
  --assets out/phase6-dg-resources --data out/native-celestial-data \
  --modules out/phase6-base-stations-engine/NativeModules --planets out/archive-data \
  --output out/performance-wayland

python3 -B Tests/Production/Performance/run.py \
  --backend x11 \
  --executable out/phase6-base-stations-engine/orbiter-production \
  --assets out/phase6-dg-resources --data out/native-celestial-data \
  --modules out/phase6-base-stations-engine/NativeModules --planets out/archive-data \
  --output out/performance-x11

python3 -B Tests/Production/Performance/verify.py \
  --wayland out/performance-wayland --x11 out/performance-x11 \
  --output out/performance-audit.json
```

All output directories must be fresh. `--smoke` runs only 80 measured intervals
and reports `smoke-only`; the complete audit rejects that mode and incomplete
case selections. The audit rechecks artifacts and sources, independently
recomputes every timing statistic and requires identical finalized physical
traces across both repetitions and both desktop backends. Source and runtime
hashes must remain stable while any benchmark process is live.

`Gate.Test.py` rejects both a copied trace with median 16 ms/p95 51 ms and a
copied capture with a 1280x720 original cockpit inside a 1920x1080 framebuffer.
The source captures remain unchanged. `Window.Test.py` rejects zero and
oversized configured dimensions before window or scene creation.

Passing this gate does not complete Phase 6. Named scenario acceptance, physical
input devices, hosted regressions, platform lifetime checks and durable evidence
preservation remain part of the complete acceptance audit.
