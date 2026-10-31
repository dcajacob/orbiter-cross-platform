# Native graphical client acceptance

Accepted on 2026-10-31 from [run 41181892596](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41181892596),
tested source `53782b1bd0da3fb7b18e636a200f34d5270330e5`. All eight jobs passed.
The final evidence/documentation commit changes no simulation or frontend code.

| Hosted check | Result |
| --- | --- |
| Ubuntu 24.04/GCC x64 Debug and Release | 10/10 suites per build, including real OpenGL rendering |
| Windows 2022/MSVC x64 Debug and Release | Native client compiled; 9/9 display-independent suites per build |
| Native four-build comparison | Every parsed numerical field identical across all three cases |
| Full Windows application Debug and Release | Builds, 2/2 existing Lua/collision suites, reference checks passed |
| Application Debug/Release comparison | Zero numerical error |
| Standalone Linux installation | Installed client runs outside checkout with installed fixture |

Linux CI uses Mesa llvmpipe, OpenGL 4.5, under Xvfb. Repeated overview,
scripted pause/single-step/camera/orbit/zoom/resize/reset/resume/follow, and free
spin all pass. Default orbit/spin runs contain 601 finalized samples over 6000
seconds; half-step numerical runs contain 1201 samples over the same duration.
GUI CSVs equal headless CSVs byte-for-byte, including the complete run following
reset. Image checks require actual primary and vessel geometry, not just HUD
pixels; they do not impose exact image equality across graphics drivers.

The controller tests every finalized state at 30/60/144 Hz and irregular frame
schedules; verifies bounded catch-up without losing pending steps; tests pause,
resume, single-step and reset; tests clock restart after a simulated hour-long OS
stall; and verifies immutable display reads, handedness and camera-relative
precision at planetary distances. All existing physics/layout/collision and
trace validation gates remain passing without changing numerical budgets.

`native-parity.json` records the unchanged frozen-reference budgets. Maximum
position error is `1.2013700229374393e-7 m` across the three native cases; velocity
error is at most `8.866990313695243e-11 m/s`; rotation, angular velocity and MJD
errors are zero. Both full Windows applications reproduce the original traces
numerically exactly. Archived comparisons, analytic checks and invariants were
independently reproduced locally from downloaded CSVs.

`provenance.json` records the source commit, all jobs, all 12 GitHub artifact IDs
and SHA256 digests, complete job-log archive digest, and the downloaded release
bundle check. `Evidence/` preserves the 12 exact provider ZIPs, all eight decoded
job logs in a separate ZIP, and local Linux evidence. Artifact digests and ZIP
integrity were checked before acceptance. Four provider artifacts contain the
native executable bundles as tar.gz archives, preserving Linux executable mode.
The downloaded Linux Release bundle was extracted and executed for 6000 steps
outside the checkout; its CSV equals the local headless CSV.

Local results are separate in `local-linux.json` and `Evidence/local-linux.zip`:
GCC 15.2/CMake 4.2.3, Debug/Release 10/10 suites, native Wayland and X11/XWayland
hardware rendering on Intel/Mesa, and normal real-time operation of the installed
client. Three real-time one-second steps produce the same finalized CSV as
headless execution. A graphics-disabled production build also produces the same
6000-step trace without any display or graphics dependency.

`Overview.png` and `Follow.png` are direct PNG encodings of the client's hardware
framebuffer captures. `CI.jpg` records the successful hosted workflow page.
The [original frozen reference](../Reference/README.md) and the previous
[headless acceptance](../Verification/README.md) remain unchanged and separate.

Windows frontend graphical runtime is not covered here; Windows coverage is
compilation, controller/numerical tests and the existing application's full tests.
This milestone supports one fixed spherical primary and one unpowered generic
vessel. It does not establish general scenario, cockpit/MFD, external asset,
module, atmosphere, terrain or ephemeris compatibility. See the
[build/run instructions and controls](../../../README.native.md).
