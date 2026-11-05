# Virtual cockpit and ISS docking in the complete stock scenes

The native Release/SSE2 package at `84706794` completes physical-input
development flows for four unchanged stock entry points:

| Scenario | Focus class | Original vessels |
| --- | --- | --- |
| `Delta-glider/Virtual cockpit.scn` | DG-S | 8 |
| `Demo/Virtual cockpit.scn` | DeltaGlider | 8 |
| `Delta-glider/Docked at ISS.scn` | DeltaGlider | 6 |
| `Demo/Docked at ISS.scn` | DeltaGlider | 6 |

Both virtual-cockpit variants respond to right-button head-look and the original
Home reset. The original RCS selector is clicked through actual 3D projection
and hit testing, then through the 2D panel, exercising modes 0, 1 and 2. Saving,
F5 reload and normal exit preserve the complete original graph.

Both docked variants save and reload the initial reciprocal GL-02/ISS
connection. Ctrl+D disengages it, and linear RCS backs the glider away from the
station. The original forward and low-power translation keys brake the motion
and fly an approach to the original free port. The production docking logic
reconnects the two vessels. Separate saved states retain the initial docked,
separated and re-docked graphs; another F5 reload preserves the final reciprocal
connection. No docking call or vessel-state setter substitutes for the approach.

All four applications exit normally. The ten graphics contexts delete normally
after a combined 6,557 successful presents. Every recorded tick retains all
declared vessels and finite states, guarded inputs remain unchanged, and
unsuppressed ASan, UBSan and leak checks report no findings. The additional SDK
observer reads state and forwards the original session call without changing its
arguments. One earlier docked driver waited for flight telemetry before the
first running tick; that failed attempt remains preserved locally.

These are development interaction results in one configuration and math
profile. Matching current Windows observations, the remaining native profiles,
the other required named flows, hardware/performance gates and full Phase 6
acceptance remain separate requirements. The last full-stock result and normal
module admission policy are unchanged. Raw evidence stays local; Windows work
uses the local VM.
