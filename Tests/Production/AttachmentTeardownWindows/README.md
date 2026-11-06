# Current Windows paused attachment cleanup

This SDK-only driver requests pause in `clbkSimulationStart`, before the first
`BeginTimeStep`, with `StartPaused = FALSE`. The Windows start-paused checkbox
performs an initial world update and therefore cannot reproduce this boundary.
The observer rejects every physics pre-step, physical-vessel update or world
finalisation, and checks the complete three-vessel roster, finite time-zero
states, reciprocal ISS docking and both Leonardo payload links on every frame.

Use `--scenario`, `ShutdownMode = 0` and sixty frames per world. `--scenariox`
selects fast process shutdown and is forbidden. The unchanged normal cleanup
branch resets the world and destroys the renderer before delivering
`clbkSimulationEnd`. A private message-only window waits until cleanup returns,
selects the original scenario in the actual launchpad tree and invokes its
normal Launch command. Twenty worlds run in one process per Debug/Release and
automatic/SSE2 profile; the launchpad closes normally after the final world.

The collector verifies actual PIDs/exits, every world/state/frame, real DLL
paths/hashes, renderer/context deletion, normal-cleanup log events and unchanged
original inputs. Windows process-heap checks and Debug CRT heap checks are
additional controls; this is not Windows ASan or leak qualification. Paused
lifetime uses actual renderer presentation counters, while image parity remains
a separate gate. Short or partial-profile runs are diagnostic only.

Both drivers compile against the current `f3e86add` Windows SDK. A two-world
Debug/automatic pilot passes, and the independent reader rejects ten damaged
copies of its evidence. The full matrix passes twenty Debug/automatic worlds,
then Debug/SSE2 crashes opening Map MFD in world seventeen, after sixteen normal
cleanups. Release profiles were not run. This is a failed matrix and provides no
complete Windows lifetime qualification. The [MFD cache regression](../MfdWorldCache/README.md)
records the resulting repair and its remaining runtime checks. Raw evidence and
the exact launch/private-desktop chain remain local. Class admission and Phase 6
completion remain separate.
