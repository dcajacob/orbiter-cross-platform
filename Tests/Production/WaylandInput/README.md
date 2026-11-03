# Actual Wayland input and framebuffer coordinates

This fixture runs a private Weston 14.0.2 headless compositor, an owned focus
destination and the real native Orbiter executable. A test seat sends Linux
key/button codes, relative pointer motion and discrete wheel events through
Weston's backend input functions. Wayland and GLFW deliver the events to the
application. No engine, camera or vessel callbacks are injected.

The compositor module accepts commands only on a socketpair inherited from the
owning harness; peer PID and UID must match. Target surfaces are matched using
Wayland client credentials and the mapped `xdg_toplevel` role. Decoration
subsurfaces are excluded. The private runtime directory has mode 0700 and is
removed after the compositor exits. Never install this module or load it into
the desktop compositor.

`dependencies.lock.json` pins official Ubuntu 26.04 amd64 Weston runtime/SDK
packages, Pixman headers and the matching original source archive. The private
backend declarations match that source's `backend.h` and
`libweston-internal.h`; they are not a general Weston ABI. Packages are
checksum-verified and extracted with `dpkg-deb -x`, without system installation.
The prepared manifest records tool source, static GLFW and output binary hashes.
The host supplies the remaining compatible runtime libraries and Wayland/XKB
development packages. This fixture currently qualifies this Linux host; it is
not a claim about Ubuntu 24.04 CI. See the upstream
[Weston test framework](https://wayland.pages.freedesktop.org/weston/toc/test-suite.html)
and the locked [Ubuntu source metadata](https://archive.ubuntu.com/ubuntu/pool/universe/w/weston/weston_14.0.2-5.dsc).

Prepare against an existing renderer build with GLFW's Wayland backend enabled:

```sh
python3 -B Tests/Production/WaylandInput/prepare.py \
  --output out/wayland-input-tools --cache out/wayland-input-cache \
  --glfw-build out/phase6-wayland-renderer
```

Run one flow in a fresh output directory:

```sh
python3 -B Tests/Production/WaylandInput/run.py \
  --dependencies out/wayland-input-tools \
  --executable out/phase6-wayland-runtime/orbiter-production \
  --assets out/phase6-dg-resources --data out/native-celestial-data \
  --modules out/phase6-wayland-runtime/NativeModules --planets out/archive-data \
  --frozen out/phase6-controls-preintegration-frozen \
  --case controls_dg_panel --configuration Release --scale 2 \
  --output out/wayland-input-dg-panel-2x
```

Repeat with `controls_dg_vc`, `controls_dgs_panel`, `controls_dgs_vc` and scales
1 and 2. The default uses verified llvmpipe and a Pixman compositor. Use
`--renderer default` for the host GPU and a GL compositor; the report rejects
llvmpipe in that mode. Each instance has its own socket and clients. The fixture
checks prepared tool hashes before execution and application/renderer hashes
before and after the session. Keep those binaries stable while any run is live.

The original Windows RCS dial coordinates and profile remain checksum-verified.
The fixture checks both dial picks, bare-W neutrality, full and one-tenth thrust,
held-key focus loss and release before focus regain. It reuses the X11 camera
assertions: cockpit/external pixel scales, no capture-entry jump, original camera
priority, original wheel/stepped-FOV behavior, pause behavior, Options ownership,
focus release and normal shutdown with the camera button held. Exact application
mouse event order and framebuffer coordinates are checked. Wayland delivers a
physical button release after GLFW's focus-loss synthetic release; both are
declared separately in the expected trace.

`verify.py --software PATH --hardware PATH --output FILE` audits two complete
eight-flow matrices. Each matrix's `matrix.json` must name exactly the four
cockpits at both scales, with successful driver exits. The audit rechecks source
hashes, independent geometry, actual renderer, compositor and application
shutdown, then joins every finalized thrust sample to its actual input tick.
Every sample without modified W must have zero RCS/exhaust; held modified W must
have the exact requested full or precision power. The audit records artifact
hashes and finalized sample counts per flow.

Scale 2 is an **engineering fixture**, requested by `window-scale.enabled` in
the explicit evidence directory. Normal window policy remains unchanged. Its
640x360 logical window must independently report a 1280x720 framebuffer and
content scale 2, with a matching compositor content surface. Wayland announces
the entered output's scale after the first buffer commit; the fixture records
blank priming presents before the original fixed-size cockpit is constructed.
Those presents are separate from engine scene presentations. Cockpit picks and
relative camera motion retain their original framebuffer units. ImGui reports
logical coordinates; the driver converts those separately. In the small logical
viewport it uses a real titlebar drag to bring the Options close button into view.

These are protocol correctness and lifecycle checks. They do not replace
physical keyboard/mouse/controller use, the named unchanged scenario acceptance
runs, cross-compositor testing, sanitizer qualification or the 1920x1080 medium
performance gate. Full Phase 6 acceptance remains separate. Frozen reference
bytes and image/numerical budgets are unchanged.
