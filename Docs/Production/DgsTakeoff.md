# DG-S takeoff in the complete stock scene

The unchanged `Delta-glider/DG-S ready for takeoff.scn` completes a native
Release/SSE2 development flow through takeoff, gear retraction, a climb above
10 km, acceleration to 700 m/s, scramjet-powered flight, saving, F5 reload and
normal exit. All eight original vessels remain present in every recorded
finalized flight state, the actual save and the reloaded scene. The application
uses the source-bound package at `84706794`; its additional observer only reads
public SDK values and forwards the original session call.

The flow enters the original virtual cockpit with F1 and visits both the 2D
panel and virtual cockpit with F8. Main throttle uses Ctrl+keypad Plus; pitch
and bank use the original keypad controls and their low-power Control variants.
G raises the gear. Keypad Multiply stops the main engines, and Alt+keypad Plus
raises scramjet throttle. Both actual scram engines reach level `0.96`, with
positive maximum thrust of approximately `45.8 kN` each. Ctrl+S saves the full
scene. No vessel state, aircraft, scenario, integrator or comparison budget is
changed to produce the flight.

The full flow waits for the replacement world to render before closing its
window. Both sessions render all eight vessels and delete their contexts after
3,993 and 50 successful presents, and the application exits normally. All
114,024 vessel-state rows across 14,253 finalized ticks are finite and preserve
the complete roster. Unsuppressed ASan, UBSan and leak checks report
no findings; all guarded inputs remain unchanged. The reloaded virtual cockpit
shows the aircraft at approximately 13 km. Earlier unsuccessful setup and pilot
attempts remain preserved locally.

A separate run also loads the exact, unedited save from an earlier completed
flight, invokes F5, and exits normally after both worlds have rendered. Its two
contexts close after 53 and 51 successful presents. This helped distinguish the
flight driver's premature close command from application reload behavior.

These results establish development flight and saved-state interaction in one
configuration and math profile. Matching original Windows observations,
complete four-profile qualification, the other named scenarios and full Phase 6
acceptance remain open. Raw evidence stays local; Windows work uses the local VM.
