# Versioned GeneralApiTest correction

`prepare.py --output NEW_DIRECTORY` retains the original script and creates a
separate test variant. Both source inputs are pinned in `inputs-v1.json`.
The original stock script, scenario, frozen source locks and planetary data
remain unchanged.

The inherited Earth period, tilt and equatorial speed use the VSOP expectations.
The locked SPICE Earth configuration declares period 86164.09983257859 s,
obliquity 0.40910170503368837 rad and radius 6371010 m. Zero precession obliquity
makes the declared tilt the fixed expected axis tilt. The independent test oracle
uses those configuration fields; surface speed is `2*pi*radius/period`.

The test variant also replaces the one-sided relative comparison with an
absolute difference at the existing relative 1e-10 budget (zero budget 1e-9),
and makes the custom assertion reject both false and nil. Non-numeric and
nonfinite comparator inputs fail. Only four declared script regions change.

`Controls.Test.py --lua LUA --output NEW_JSON` executes the generated helpers
with harmless logging sinks: 22 Lua checks cover correct/incorrect values,
both signs and sides, nil, false and truthy Lua values. Three damaged source/model
controls are rejected. These are helper controls only. Corrected-script Windows
and native simulator runs, their original failures, normal-host intentional-exit
policy and final admission evidence remain required before qualification.

The initial focused Debug/automatic native diagnostic preserves the original
planet-status failure and reaches `All tests passed` with the corrected variant.
Both contexts close with no sanitizer finding. The corrected test calls
`oapi.exit(0)` during startup and presents zero frames; normal corpus acceptance
therefore still requires the matching Windows run and an explicitly qualified
startup-exit policy. This result does not close the four-profile API gate.
