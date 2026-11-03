# Original Lua and AAP reference candidate

This gate uses the preserved original Windows application, SDK, Lua libraries
and OpenGL client. Its additional observation plugin exercises synchronous
execution, queued command concatenation, synchronous execution while an async
command is pending, four frame yields, independent interpreter globals and
explicit interpreter destruction.

The DG and DG-S cases also load the actual stock `dg/aap` script into a real
interpreter, attach the actual vessel interface, run altitude/speed/bank
controllers and stop them. Finalized control-surface values are recorded along
with the existing vessel states, instrument text, geometry and rendered images.
The orbital fixtures isolate scheduling and SDK bindings. Two additional
fixtures use the actual atmospheric vessel state blocks from Animated control
surfaces and Cruising above Florida at the common reference epoch. They require
positive density/dynamic pressure, speed-command retargeting and real control
surface rundown. They are reduced fixtures, distinct from complete stock
scenario acceptance.

Each case runs twice per Windows Debug/Release build. Exact Lua event and
control traces, the existing numerical/image budgets and successful original
shutdown are required. References remain candidates until the runs and their
cross-build comparison pass and provenance is preserved.
