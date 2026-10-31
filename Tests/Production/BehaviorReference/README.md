# Frozen pre-extraction production behavior

Accepted from hosted [run 41193020450](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41193020450).
The observation/control driver is source `684bd5b27005feecfa9effe796bd216f85e3392f`.
The actual MSVC-built application and SDK are from source
`06d8989823c59e651061d409425c19ec71360bfa`, runtime
[run 41192125192](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41192125192).
Every production source byte matches the frozen pre-extraction revision after
removing explicitly marked test-only observations. The public Windows SDK is
unchanged. The full application, existing tests and original immutable numerical
references pass with these observations enabled.

All fourteen cases pass twice in native Windows MSVC x64 Debug and Release:
all twelve RCS groups, five autopilot modes, atmospheric DG-S flight, landed and
descending terrain contact at Edwards, docked/undocking and automatic ISS
docking, attachment/detachment, pause/warp/resume, vessel creation/deletion/focus,
DG-S animations, finalized save, stock reload and callback ordering. The
automatic docking event occurs at tick 250. Atmosphere modules are source-built
and staged at their existing CMake install paths; missing modules fail explicitly.

Every repeat's four CSV files is byte-identical. Hosted Debug/Release comparison
passes the unchanged budgets, including exact tick/input/callback sequence.
Maximum position difference is zero; velocity is below `4.6e-13 m/s`, attitude
below `3.1e-15 rad`, and angular velocity below `1.3e-14 rad/s`. Mass, fuel and MJD
differences are zero. These budgets were not widened after a failing candidate.

The save occurs after state finalization and time advancement. Reload is tested
against the original format's decimal precision separately: the DG-S position
round trip differs by about `0.00020 m` and velocity by `0.000047 m/s`.
The usual velocity budget is unchanged for comparisons between executions of
the same round-trip fixture. Stock saved fields and all animation identities/
states are checked, including gear, nosecone, passengers and tank configuration.

`provenance.json` locks the original artifact ZIPs and their members, application
and driver sources, fixture/control manifest, data profiles and budgets. It has
no automatic refresh path. Run from the repository root:

```sh
python3 -B Tests/Production/frozen_behavior.py
python3 -B Tests/Production/frozen_behavior.py --candidate /path/to/production-behavior --configuration Release
```

For a new Windows capture, use `behavior_suite.py --orbiter <source-built exe>
--data <verified stock profile> --planets <verified standard archives>
--output <new directory> --configuration Release`, then the frozen comparator.
The dedicated workflow verifies and reuses the entire source-built SDK/runtime
before compiling the current driver; any engine/SDK change rejects that reuse.

These are reduced engineering fixtures running real production systems. They
do not replace stock-corpus initialization, graphical-client execution, cockpit
acceptance, or the later interactive flights.
