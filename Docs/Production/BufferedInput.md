# Buffered keyboard modifiers

A current Debug/SSE2 run of the unchanged six-vessel Docked at ISS scene
undocked and braked successfully, then missed Ctrl+S. Its input trace records
the Ctrl press, S press and both releases at input tick 1727. All four were
interpreted using the final held-key snapshot, in which Ctrl was already up.
The separated state was therefore not saved. That failed run and its clean
application exit remain preserved locally.

Native buffered dispatch now reconstructs the key state before the queued
edges and advances it for each event. Shortcuts, vessel callbacks and MFD
routing receive that event's modifiers. Continuous controls retain the actual
held-key snapshot. The input record layouts, public SDK, vessel-first dispatch
priority and original physics are unchanged.

`Production.BufferedKeys` covers all six modifier keys with S, Space and I,
a modifier held across polls, a modifier pressed after the command key, and
all 32 poll partitions of a mixed Ctrl/Shift chord. The complete portable
sanitizer suite passes 38 tests, and the original source conservation audit
passes. The exact committed helper also compiles and passes its console
regression with local Windows MSVC in Debug and Release.

The fresh `6a67588b` Debug/SSE2 application now completes all four unchanged
Virtual cockpit and Docked at ISS entry points with their original eight or six
vessels. Every Ctrl+S chord is deliberately delivered in one real Wayland input
batch. Both docking variants save the initial connection, the separated state
and the automatic re-docking, then preserve the connection through F5 reload.
All four applications and their graphics contexts close normally with clean
unsuppressed sanitizer logs and unchanged guarded inputs.

A separate full eight-vessel DG orbit run also passes both Ctrl+Space control
dialogs, original Ctrl+P pause/resume and Ctrl+S save with all five modified
chords delivered as complete batches. The remaining native build profiles and
matching full Windows flight observations remain required for qualification.
These checks do not complete Phase 6.
