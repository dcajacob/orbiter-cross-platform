# Current local Windows qualification

Fresh Debug and Release application/SDK/client builds at `f3e86add` pass the
existing ordinary-scene, SurfaceDC GDI, nine cockpit-fixture and five control-
fixture gates, with both scene repetitions. The eleven canonical gate processes
complete 64 fresh scene repetitions. Both builds pass all 22 unit tests.
Independent Linux re-reading passes all three Debug/Release comparisons;
ordinary-scene and frozen image SSIM are 1.0.

The completed local VM chain retains the guest-agent launcher, normal-user
bootstrap, actual worker, private desktop, eleven gate-process PID/exit receipts
and closed-desktop result. The historical canonical collector does not retain
separate PID receipts for all 64 simulator launches; its source-bound checked
subprocess calls and actual scene outputs remain preserved. This is not a
claim of 64 individually recorded launch receipts.

The independent audit verifies 9,454 preserved source/dependency/build/runtime
archive members and all 15,213 observation files. It compares source bytes with
the immutable application commit and runner bytes with `b6f9a1a0`, checks input
and runtime guards, and independently re-runs the original comparators. The
[verification record](CurrentWindowsVerification.json) pins that local audit.
All raw evidence remains local; no hosted build or evidence upload was used.

These results belong to the stated source. They do not qualify the subsequent
MFD-cache repair. The separate [normal-cleanup lifetime regression](../../Tests/Production/AttachmentTeardownWindows/README.md)
subsequently failed during its Debug/SSE2 restart campaign. Complete remaining-
mission persistence, class admission, controllers, hardware/performance and
Phase 6 acceptance remain open.
