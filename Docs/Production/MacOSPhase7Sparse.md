# macOS Phase 7 sparse results

The native Release desktop checks passed on Intel (`x86_64`) and Apple Silicon
(`arm64`) at `f2fead9d259e93fd9fbfd3c432eda982030f2ec5`. Both jobs used standard
GitHub-hosted macOS 15 runners, Cocoa windows at 1280×720, and Apple’s software
OpenGL renderer. The test scenario was the unchanged stock **DG Mk4 in orbit**.
[Desktop run 43661909716](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/43661909716)

| Check | Verified on both architectures |
| --- | --- |
| Qt Launchpad | Selected and opened the stock Delta-glider flight, hid while Orbiter ran, and reappeared on clean exit with the same scenario selected and ready to launch again. A test wrapper gave the real simulator a 12-frame exit limit. |
| Options | Changed MFD refresh to 0.35 s, MFD size to 7, panel scale to 1.1, and limited fuel to off using the live dialog. A fresh process read all four saved values from the same configuration file. |
| Paused scenario editor | Added, moved, and removed a stock ShuttlePB. The move retained velocity and fuel. Fresh processes reopened the exact saved files and confirmed the recorded move and deletion. Both architectures used the original Linux sparse reload tolerances of 0.001 m and 0.0001 m/s. |
| XRSound | Core Audio initialized in the original and reloaded flights. The Delta-glider’s main-engine and RCS voices both started and stopped in each process. |

The earlier production stock-flight check on both architectures at
`39d93da2010cfcdeb60005543f2179131ec831ba` verified all eight original vessels,
60 successful presentations, and clean Cocoa teardown.
[Stock flight run 43660309872](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/43660309872)

Physical Mac GPU, speaker, and controller acceptance remain open. Coverage here
is limited to the scenarios and actions above. Full stock and mission runs
remain deferred.

## Retained evidence

The two desktop archives were verified against the GitHub artifact digests and
retained locally under `out/macos-phase7-desktop-v1/run-43661909716/`. The
`audited-results.json` receipt records source identity, configuration
persistence, the exact scenario inputs, and the separate reload processes.

| Architecture | GitHub artifact ID | Archive SHA-256 |
| --- | --- | --- |
| Intel | `14140893184` | `ee72e0c162498a0fe25c80370e20c6f94fc3fcce53c3637dfed7de9b5b3a9bd4` |
| Apple Silicon | `14140362933` | `a285e00cc0585b346af9c1ac154b31c176c77dfbdea342eacf9bfc4572c76563` |
