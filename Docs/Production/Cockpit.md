# Phase 6 cockpit and instrument integration

Phase 6 is in progress. Phase 5 remains accepted; the prepared laptop preview is
still the verified production ShuttlePB/ISS external-view build. No native
cockpit or Delta-glider capability is claimed by the engineering probes below.

The first gate executes the original Windows application and SDK at
`d14fa7941bd4b60bd5b07c8e444ebfb87761893f`, from accepted Phase 5 runtime
artifacts in run 41396231165. The complete original application/SDK file hashes
and matching owning sources are checked before compiling the SDK-only control
driver. Pane, HUD, MFD, panel, VC, DG and DG-S implementations remain unchanged.

The real Windows OpenGL client receives opt-in text/readback observation hooks.
They record actual Sketchpad calls, original displayed numbers, surface identity,
font height and color, plus complete 1280x720 frames at ticks 20 and 50. They
forward the existing drawing path without replacing instrument calculations or
geometry. The same hooks are available in the shared native renderer but are
disabled for ordinary runs and previous regression fixtures.

Nine reduced probes cover all ten stock MFD modes, all three HUD modes, and real
DG/DG-S 2D panels/virtual cockpits. Every probe runs twice with 60 quarter-second
physics steps. The driver paces software rendering by 120 ms per frame so the
unchanged stock 10 Hz wall-time MFD limiter does not discard updates. Simulation
clocks, numerical formulas and the MFD scheduler are unchanged. The FPS, menu and
information bars are hidden; no image masks are used.

Before extraction, require repeat-identical numerical and displayed-text traces,
finite finalized state, actual expected cockpit/MFD modes, numerical display
calls, normal real window/context teardown, no GL errors and SSIM at least 0.98.
The original orbital/propulsion budgets remain unchanged. Failed probes are
diagnostics, never accepted references. Capturing a golden requires successful
Debug/Release repeats and cross-configuration comparison; accepted references
will not be refreshed automatically.

After this gate, extract original instrumentation and panel/VC services behind
explicit platform boundaries. Keep Windows adapters, preserve calculations and
callback order, and add native surface/blit/font/mesh/input support through the
shared renderer. Then source-build DG/DG-S, compare original displayed precision,
validate picking and controls on the actual vessel, and run the required stock
scenarios. A prototype overlay cannot satisfy these gates.
