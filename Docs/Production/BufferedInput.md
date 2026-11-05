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
passes. Fresh full-application interaction and remaining profile qualification
are still required; these checks do not complete Phase 6.
