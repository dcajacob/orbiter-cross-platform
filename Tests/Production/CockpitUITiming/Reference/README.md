# Original Windows fixed-clock cockpit UI reference

[Run 41551358542](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41551358542)
captured Orbit target selection, Sync list length entry and input cancellation
twice in both Windows Debug and Release at d5bf06b4. Each process used the
original f7251942 application and SDK and the 68400a7d OpenGL client from the
parent reference. The test driver observed ImGui frames 0 through 59 with a
0.25-second delta in every case. The GUI continued to draw its own caret.

Both builds produced the same finalized vessel states, input events, popup
geometry, callbacks, display text and HUD atlas updates. At frames 20 and 50,
the full images and both MFD surfaces had SSIM 1.0. The archive digests and all
607 capture files per configuration are pinned in provenance.json. The capture
workflow accepts manual runs only. The original wall-clock reference remains
available for whole-frame comparisons.
