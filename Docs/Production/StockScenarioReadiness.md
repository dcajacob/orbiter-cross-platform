# Complete stock-scenario readiness baseline

All **157 unchanged locked scenarios** were attempted on the Release automatic
runtime from `9418ae29`. The audited result is **44 passed and 113 failed**.
This is an initialization/readiness baseline, not full corpus acceptance.
Every failure is retained; none is converted into a pass because it was expected.

The successful scenarios complete 60 frames, normal graphics-context deletion
and all finalized vessel states at ticks 0 through 60. Every declared ship and
class, including non-focus objects, must be present at every tick. A negative
control removes a non-focus ship at tick 30 from a copied real capture: the gate
rejects it despite normal presentation and teardown. Original captures remain
unchanged.

The failures retain two prerequisite groups:

| Cause | Scenarios | Evidence |
| --- | ---: | --- |
| Missing staged vessel configurations and corresponding source modules | 112 | Actual startup failures and the configuration/module inventory |
| GeneralApiTest Earth-obliquity assertion | 1 | Sixty frames complete, but the same stock assertion previously failed in all four preserved Windows profiles |

Mir and Wheel intentionally declare no Module entry. The existing original
base VESSEL configuration path handles their meshes, mass, inertia and docking
data. Their additional Windows observations and local Release automatic native
comparisons now pass. The host admits their explicit observed capabilities;
declared modules remain mandatory. This makes seven formerly rejected scenarios
pass, improving the previous `2c00d29b` baseline from 37/120 to 44/113. The
preflight's 45 file-ready scenarios are not 45 runtime passes: GeneralApiTest
still fails its assertion. [Station qualification](StockStations.md)

Twenty-five dependency-incomplete scenarios terminate by signal in this
historical sweep. A subsequent fully instrumented runtime now rejects all 25
unchanged scenes cleanly, with normal context deletion and no sanitizer findings.
It also checks both SDK creation signatures. The fix handles unresolved dock
tokens and releases class names and temporary parsed docking records. All 25
remain failed stock scenarios because their dependencies are unavailable.
[Startup lifetime evidence](VesselStartupLifetime.md) is separate from full
corpus acceptance; a fresh complete instrumented sweep is in progress.

ShuttleA configuration/module dependencies affect 85 scenarios. Atlantis affects
30. Other missing classes include Carina, Atlantis tank/SRB, Leonardo MPLM,
Dragonfly, HST, ShuttleA payload, LDEF, SolarSail and Quadcopter. These class
counts overlap because one scenario can need several modules.

The named acceptance scenarios remain intact:

| Named unchanged scenario | Missing staged dependency |
| --- | --- |
| DG Mk4 in orbit, with all eight objects | ShuttleA |
| Virtual cockpit | ShuttleA |
| DG-S ready for takeoff | ShuttleA |
| Docked at ISS | ShuttleA |
| Atmospheric autopilot | ShuttleA |
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
