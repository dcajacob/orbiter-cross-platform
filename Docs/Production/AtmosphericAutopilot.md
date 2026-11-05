# Complete atmospheric-autopilot tutorial

The `6a67588b` native packages complete the unchanged eight-vessel
`Delta-glider/Atmospheric autopilot.scn` tutorial in Debug/Release and
automatic/SSE2 profiles. Each run uses its package's matching SDK, vessel
modules and renderer.

Real Wayland keys operate the original Terminal MFD and its input dialog. The
flow verifies the vessel binding, connects aerodynamic controls with Alt+Divide,
sets 300 m/s, rotates with the keypad, retracts the gear and commands a 10 km
altitude. It then sets 600 m/s and 20 km, operates the scramjets, performs the
instructed manual climb above 24.5 km, releases control to the autopilot and
commands 250 m/s. Each run passes the fifteen recorded instruction checkpoints,
reaches the tutorial conclusion and executes `help(dg_aap)`. Ctrl+S saves the
complete scene.

| Profile | Complete eight-vessel ticks | Finite vessel-state rows | Successful presents |
| --- | ---: | ---: | ---: |
| Release/SSE2 | 40,885 | 327,080 | 13,349 |
| Debug/SSE2 | 40,932 | 327,456 | 11,372 |
| Debug/automatic | 40,878 | 327,024 | 11,631 |
| Release/automatic | 40,716 | 325,728 | 12,319 |

All four applications exit normally and delete their graphics contexts. Every
recorded finalized tick and every save retains all eight original vessels.
An independent local read checks all 1,307,288 state rows for finite values and
the complete roster at each tick. It also checks the original Terminal commands,
instruction checkpoints, saved rosters, graphics teardown and 1,036 distinct
guarded files. Unsuppressed ASan, UBSan and leak checks report no findings.

These are complete native functional tutorial flows. They use the existing
successful pilot and original scenario, script, controls and thresholds; the
observer reads SDK state and forwards the original session calls. No vessel
state setter or propagation change produces the flight. Matching original
Windows trajectories, clocks, images and inputs, the other named scenarios,
hardware/performance and full Phase 6 acceptance remain open. Raw evidence
stays local; Windows builds and runs use the local VM.
