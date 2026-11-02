# Ground-flight candidates that were not accepted

No existing frozen reference or numerical tolerance was replaced by these runs.
The native application, production physics and stock vessel remained unchanged
throughout this investigation.

## Initial 20 Hz hop

The initial candidate used one RK4 step per 0.05-second tick and left horizon
hold active after contact. The native and Windows snapshots reported ground
contact, but the original Windows exit save still said `STATUS Orbiting Earth`:
the vessel had not completed a landing. The original native host showed the same
problem. Releasing horizon hold alone did not complete a landing in that profile.

At the native host's normal 60 Hz tick, releasing horizon hold at 20 seconds and
cutting hover at 35 seconds lets the unchanged original vessel reach
`STATUS Landed Earth` before 60 seconds. The revised reference must prove that
state through both `VESSELSTATUS2.status` and the original saved scenario. Merely
touching the surface cannot satisfy its gate. Reference input durations remain
unchanged; tick indices scale with the application's normal physics rate.

The first native 20 Hz hop had identical traces when rendering every 4, 5 or 17
ticks. Disabling base-mesh collision in a separate diagnostic also left its trace
unchanged. Its late contact trajectory exceeded the declared attitude/fuel
budgets. Those failures are retained; the coarse profile is not claimed as
accepted ground-flight support.

## Preserved Windows evidence

The first six-case capture is
[run 41366192542](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41366192542).
Both Windows configurations repeat identically; the comparison job failed because
the initial artifact layout was wrong.

The seven-case captures at `df7691db` and `387cbb73` are
[run 41366429833](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41366429833)
and [run 41366773807](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41366773807).
Their initial comparison incorrectly applied an orbital spin tolerance to
contact. The comparison implementation was corrected to the agreed contact
criteria, retaining every existing frozen reference and every agreed threshold.
PB angular velocity remains reported, and the ISS retains its strict orbital
budget. The corrected comparison passes these Windows traces locally, including
the unchanged mass/propellant budget. It still rejects the late native hop.

Original artifacts from run 41366773807:

| Artifact | SHA256 |
| --- | --- |
| ground-flight-reference-Debug | `90934f0fa9bf976a58209654e4e8cd6d1f344df3c8fe685751689e7e4834003d` |
| ground-flight-reference-Release | `d35905c38eba82a7317029a47eef5290a6a84065ccf8a0eaccd72bfbeb6e8515` |

The candidate at `4fb97c8e` applies the corrected criteria, but predates the
stronger requirement for an actual completed landing. It is not a frozen
reference. Hosted artifacts/logs and local `out/production-cache/ground-*` and
`out/native-ground-bringup/` retain the captures and diagnostics separately from
the accepted orbital preview.
