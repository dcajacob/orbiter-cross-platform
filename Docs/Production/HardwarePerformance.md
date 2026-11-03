# Phase 6 Intel desktop performance

The local Release automatic renderer passes the fixed 1920x1080 medium gate on
the laptop's real Wayland and XWayland desktops. Twelve fresh application
processes complete 25,920 scene presentations. The audit retains all 21,600
declared measured intervals: every run has median at most 33 ms and p95 at most
50 ms. The worst median is 22.37 ms and worst p95 is 25.35 ms.

Each row below reports the worse result of two repetitions. The maximum column
retains the worst single interval, including desktop stalls; it is not an added
acceptance limit. No outliers are removed.

| Desktop | Unchanged stock scene | Median ms | p95 ms | Maximum ms |
| --- | --- | ---: | ---: | ---: |
| Wayland | Edwards AFB exterior | 22.37 | 25.35 | 53.30 |
| Wayland | Geostationary 2D panel | 19.04 | 21.50 | 45.62 |
| Wayland | Mojave virtual cockpit | 22.25 | 24.52 | 44.88 |
| XWayland | Edwards AFB exterior | 8.52 | 11.95 | 139.12 |
| XWayland | Geostationary 2D panel | 8.49 | 14.13 | 192.11 |
| XWayland | Mojave virtual cockpit | 8.75 | 12.58 | 107.98 |

The profile was fixed before the full measurement: 360 warmup frames followed
by 1,800 measured intervals, two fresh-process repetitions per scenario and
desktop. The scenes are exact stock bytes, with no deleted objects or edited
camera blocks. Medium uses the middle planetary patch-grid choice (64 segments),
maximum surface level 18, zero resolution bias and the declared original visual
features. Original physics defaults and one original 1/60-second tick per
rendered frame are retained. All finalized physical traces are byte-identical
across both repetitions and both desktop backends.

The primary metric is consecutive `glfwSwapBuffers` return cadence. It includes
polling, original physics, GUI, rendering, swapping, application bookkeeping and
timing-write overhead. Poll-to-return and swap durations remain available in the
raw audit. It measures steady application throughput rather than physical
display latency. Measurements run serially on AC power with the actual Intel
PTL Mesa driver. No system driver, desktop, governor or power settings change.

Configured native `WindowWidth` and `WindowHeight` now request framebuffer
pixels. Wayland startup settles the actual entered surface's scale before the
original fixed-size cockpit is created. On this desktop the surface reports
scale 1.25, producing a 1536x864 logical window and an exact 1920x1080 framebuffer.
The integer output-scale hint differs from that fractional feedback. XWayland
uses a 1920x1080 client/framebuffer even though its font content scale is 2.
Both backend geometry checks are independent of the requested dimensions.
Blank pre-scene buffer commits used for Wayland negotiation are recorded
separately. Sessions without explicit dimensions retain the established default
window policy.

A negative control gives a synthetic trace median of 16 ms and p95 of 51 ms;
the unchanged p95 gate rejects it. Zero and oversized configured dimensions
fail explicitly before window or scene creation. Default-window camera and
input regressions remain separate evidence for this renderer. The accepted
Windows reference bytes, image masks and numerical budgets are unchanged.

[Machine-readable qualification and artifact hashes](HardwarePerformanceVerification.json)
[Fixed profile, timing method and reproduction](../../Tests/Production/Performance/README.md)

This closes the local hardware performance checkpoint at the declared profile.
Physical input devices, the complete named scenario acceptance, remaining vessel
dependencies, hosted qualification, platform lifetime checks and durable final
evidence preservation remain part of the full Phase 6 audit.
