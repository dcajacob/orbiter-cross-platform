# Phase 6 Intel desktop performance

The local Release automatic renderer passes the fixed 1920x1080 medium gate on
the laptop's real Wayland and XWayland desktops. Twelve fresh application
processes complete 25,920 scene presentations. The audit retains all 21,600
declared measured intervals: every run has median at most 33 ms and p95 at most
50 ms. The worst median is 22.64 ms and worst p95 is 25.31 ms. The original
cockpit and camera now use the actual 1920x1080 framebuffer dimensions.

Each row below reports the worse result of two repetitions. The maximum column
retains the worst single interval, including desktop stalls; it is not an added
acceptance limit. No outliers are removed.

| Desktop | Unchanged stock scene | Median ms | p95 ms | Maximum ms |
| --- | --- | ---: | ---: | ---: |
| Wayland | Edwards AFB exterior | 22.64 | 25.31 | 43.47 |
| Wayland | Geostationary 2D panel | 18.92 | 21.41 | 41.22 |
| Wayland | Mojave virtual cockpit | 22.48 | 24.98 | 47.67 |
| XWayland | Edwards AFB exterior | 8.46 | 11.26 | 127.95 |
| XWayland | Geostationary 2D panel | 8.59 | 15.16 | 102.93 |
| XWayland | Mojave virtual cockpit | 8.50 | 11.63 | 98.18 |

The profile was fixed before the full measurement: 360 warmup frames followed
by 1,800 measured intervals, two fresh-process repetitions per scenario and
desktop. The scenes are exact stock bytes, with no deleted objects or edited
camera blocks. Medium uses the middle planetary patch-grid choice (64 segments),
maximum surface level 18, zero resolution bias and the declared original visual
features. Original physics defaults and one original 1/60-second tick per
rendered frame are retained. All finalized physical traces are byte-identical
across both repetitions and both desktop backends.
They also remain byte-identical to the preceding runtime's physical traces.
The complete matrix is repeated after `9418ae29` restores the original shared
base-texture initialization and cleanup. The viewport-correct `c079e79e` captures
and their evidence bundle remain preserved as an earlier qualification.

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

A source audit found that the preceding `2c00d29b` qualification checked the
1920x1080 renderer while the native host still constructed the original cockpit
and initially sized the camera at 1280x720. That result is superseded by this
freshly built runtime and complete repeated matrix. The host now queries the
opened graphics client's viewport, following the original Windows application,
and passes those dimensions at the existing cockpit/camera initialization
points. The gate independently checks the original cockpit's reported size.
The earlier raw captures and local evidence archive remain preserved as history.

A negative control gives a synthetic trace median of 16 ms and p95 of 51 ms;
the unchanged p95 gate rejects it. Another retains the correct framebuffer but
substitutes a 1280x720 cockpit observation; the dimension gate rejects it.
Zero and oversized configured dimensions
fail explicitly before window or scene creation. Default-window camera and
input regressions remain separate evidence for this renderer. The accepted
Windows reference bytes, image masks and numerical budgets are unchanged.

[Machine-readable qualification and artifact hashes](HardwarePerformanceVerification.json)
[Fixed profile, timing method and reproduction](../../Tests/Production/Performance/README.md)

This closes the local hardware performance checkpoint at the declared profile.
Physical input devices, the complete named scenario acceptance, remaining vessel
dependencies, hosted qualification, platform lifetime checks and durable final
evidence preservation remain part of the full Phase 6 audit.
