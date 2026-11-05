This diagnostic measures the original Windows application's paused docked
serialization at the two native canaries' observed pause ticks: 293 and 272
steps of 1/60 s. Both complete six-object stock entry points, original epoch,
all module fields and original default propagators remain unchanged.

The separate SDK module sends three original buffered F8 keys and two H keys,
requests pause through `oapiSetPause`, and saves through `oapiSaveScenario`.
A second fresh original process loads those exact saved bytes and requests
pause in `clbkSimulationStart`, before its first `BeginTimeStep`. Every reload
physics callback or nonzero simulation time fails. The legacy `StartPaused`
configuration option is kept false because the original application deliberately
performs one running initialization step for that option. No original program,
module, SDK, scene or physics code is patched.

All four Debug/Release automatic/SSE2 profiles run both entry points twice.
Complete rosters, actual source-built interfaces/DLLs, finite physical states,
exact paused clocks, normal real rendering, unchanged original inputs and exact
repeats are checked. Every semantic-token change across the original paused
save/read/write is retained. A completed diagnostic does not imply zero deltas,
a new numerical allowance, a refreshed frozen reference, native docking
acceptance, full stock acceptance or Phase 6 completion.

The workflow reuses the exact already accepted original application, SDK and
captured OpenGL client, with their frozen package and file hashes. It has no
release, artifact, runtime, SDK or provider upload step. Concise normal CI test
results may be retained locally alongside native evidence; evidence archives
remain local.

The diagnostic records a read-only Win32 snapshot of its own actual DLL paths
at the paused save and verifies the required application, observer, original
vessel, renderer and Mesa module hashes. This does not depend on the frozen
renderer reaching its later image-capture time. No physics, save, input, clock,
module byte or reference criterion changes with this observation.
