# Complete stock-scenario readiness baseline

All **157 unchanged locked scenarios** were attempted on the Release automatic
runtime from `2c00d29b`. The audited result is **37 passed and 120 failed**.
This is an initialization/readiness baseline, not full corpus acceptance.
Every failure is retained; none is converted into a pass because it was expected.

The successful scenarios complete 60 frames, normal graphics-context deletion
and all finalized vessel states at ticks 0 through 60. Every declared ship and
class, including non-focus objects, must be present at every tick. A negative
control removes a non-focus ship at tick 30 from a copied real capture: the gate
rejects it despite normal presentation and teardown. Original captures remain
unchanged.

The failures identify three separate prerequisites:

| Cause | Scenarios | Evidence |
| --- | ---: | --- |
| Missing staged vessel configurations and corresponding source modules | 112 | Actual startup failures and the configuration/module inventory |
| Mir/Wheel rejected by the current host capability guard | 7 | Their original configuration-defined vessels load, then the explicit host restriction rejects them |
| GeneralApiTest Earth-obliquity assertion | 1 | Sixty frames complete, but the same stock assertion previously failed in all four preserved Windows profiles |

Mir and Wheel intentionally declare no Module entry. The existing original
base VESSEL configuration path handles their meshes, mass, inertia and docking
data. They require qualification and an explicit host policy change, not a fake
module or a generic replacement for a missing DLL. Declared modules remain
mandatory. The preflight's 45 file-ready scenarios are not 45 runtime passes;
only the actual 37 complete cleanly.

ShuttleA configuration/module dependencies affect 85 scenarios. Atlantis affects
30. Other missing classes include Carina, Atlantis tank/SRB, Leonardo MPLM,
Dragonfly, HST, ShuttleA payload, LDEF, SolarSail and Quadcopter. These class
counts overlap because one scenario can need several modules.

The named acceptance scenarios remain intact:

| Named unchanged scenario | Missing staged dependency |
| --- | --- |
| DG Mk4 in orbit, with all eight objects | ShuttleA; Mir/Wheel qualification is also required |
| Virtual cockpit | ShuttleA; Mir/Wheel qualification is also required |
| DG-S ready for takeoff | ShuttleA; Mir/Wheel qualification is also required |
| Docked at ISS | ShuttleA; Mir/Wheel qualification is also required |
| Atmospheric autopilot | ShuttleA; Mir/Wheel qualification is also required |
| DG to the moon tutorial | ShuttleA |
| Atlantis ISS Resupply | Atlantis and Leonardo MPLM |

No ship is deleted to bypass those dependencies. Further production module
changes require matching original Windows observations before native
qualification. The current sweep does not establish physical interaction,
wall-clock Today semantics, or new original-Windows image/state parity for
these full scenarios.

The frozen scenario file hashes all match. Seven old inventory metadata entries
misparsed indented blocks or vessel properties; the new parser derives ship
identities from the locked bytes and reports that metadata discrepancy. The
frozen lock itself is unchanged.

[Machine-readable baseline and artifact hashes](StockScenarioReadiness.json)
[Full-corpus driver, audit and controls](../../Tests/Production/StockScenarios/README.md)
