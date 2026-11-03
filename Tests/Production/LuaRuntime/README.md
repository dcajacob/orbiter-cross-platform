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
positive density/dynamic pressure, low/high/low speed-command retargeting and real control
surface rundown. They are reduced fixtures, distinct from complete stock
scenario acceptance.

Each case runs twice per Windows Debug/Release build. Exact Lua event and
control traces, the existing numerical/image budgets and successful original
shutdown are required. References remain candidates until the runs and their
cross-build comparison pass and provenance is preserved.

The paired capture runs on both Windows Server 2022 and 2025, with Debug and
Release on the same worker for each OS. The 2022 comparison and its artifact
names remain unchanged. The 2025 artifacts use the `original-lua-aap-windows2025`
prefix. Both apply the same default-profile gate and separate forced-SSE2
diagnostic. No reference or numerical budget is changed by this host comparison.

The [CRT diagnostic](../CrtDiagnostic/README.md) established that Windows 2022
loads different CRT version families for Debug and Release. On Windows 2025,
both providers belong to the 26100 family and their 8,517 arcsine outputs agree
in every tested profile. Full simulator captures are required to determine
whether that runtime provisioning also resolves the Lua/AAP mismatch.
