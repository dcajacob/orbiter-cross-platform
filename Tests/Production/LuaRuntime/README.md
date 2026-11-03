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

In [run 41588025808](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41588025808),
both Windows 2022 captures passed individually, but their default-profile
comparison still failed on 21 atmospheric DG control samples. The separate
SSE2 comparison passed every case, including images and exact control traces.
Windows 2025 Debug passed, while Release's orbital DG case resumed `yield_3`,
`yield_4` and `yield_done` at the same simulation time, 5.5 seconds. Its other
four completed cases have identical Debug/Release event, control, atmosphere,
controller, horizon and cockpit-state CSV bytes in both repeats. The incomplete
DG case prevents acceptance of the complete set. The checks and budgets remain
unchanged. [`host-diagnostic.json`](host-diagnostic.json) retains the input
identities, failure details and exact-trace hashes.

The current native Debug client also passes the shared schedule for all five
cases against the Windows 2025 Debug artifact. Its event timing, controls,
atmospheric values and complete cockpit-state CSVs match exactly. This checks
the native handoff and SDK path; it does not accept the failing original
Windows Release set or qualify native Release.

The preserved interpreter releases its execution mutex, then waits through a
second mutex to reacquire execution. If the simulator is descheduled between
its release and wait, the worker can reacquire both mutexes without a simulator
turn. This is a source-based hypothesis for the observed frame collapse;
the observation alone does not prove the interleaving. Windows mutexes do not
promise [FIFO ownership](https://learn.microsoft.com/en-us/windows/win32/sync/mutex-objects).
`HandoffDiagnostic.cpp` models that specific preemption with actual Win32
mutexes and compares it with the native explicit-turn handoff. Its diagnostic
result is separate from simulator acceptance.

The Windows observer also records `lua-timing.csv`: performance-counter values,
thread IDs, simulation times, original frame boundaries and the existing Lua
audit events. Its additional Lua C callback observes timing through the loaded
original library. It does not manipulate the interpreter's private mutexes or
simulation clocks. The shared native schedule has no installed timing callback.
These records help distinguish a fast worker reacquisition from a stalled
frame; collecting them does not itself resolve the failure.

CI runs each OS comparison even when a capture on the other OS fails, and still
collects the SSE2 diagnostic after a failed default capture. Failed or missing
captures remain rejected. Comparison failures now produce a JSON report with
input statuses, so skipped work and rejected evidence remain visible.
