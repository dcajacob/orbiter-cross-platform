# Versioned GeneralApiTest correction

`prepare.py --output NEW_DIRECTORY` retains the original script and creates a
separate test variant. Both source inputs are pinned in `inputs-v2.json`.
`--version v1` still reproduces the earlier diagnostic variant.
The original stock script, scenario, frozen source locks and planetary data
remain unchanged.

The inherited Earth period, tilt and equatorial speed use the VSOP expectations.
The locked SPICE Earth configuration declares period 86164.09983257859 s,
obliquity 0.40910170503368837 rad and radius 6371010 m. Zero precession obliquity
makes the declared tilt the fixed expected axis tilt. The independent test oracle
uses those configuration fields; surface speed is `2*pi*radius/period`.

The test variant also replaces the one-sided relative comparison with an
absolute difference at the existing relative 1e-10 budget (zero budget 1e-9),
and delegates the logging assertion to Lua's built-in assertion, preserving
nil/false failures, truthy return values, extra returns and custom messages. Non-numeric and
nonfinite comparator inputs fail. Only four declared script regions change.

`Controls.Test.py --lua LUA --output NEW_JSON` executes the generated helpers
with harmless logging sinks: 26 Lua checks cover correct/incorrect values,
both signs and sides, nil, false and truthy Lua values. Three damaged source/model
controls are rejected. These helper controls are distinct from simulator evidence.

The complete four-profile Windows/native test matrix is independently audited
in the local closeout ledger. Every original run retains its planet-status
failure; every corrected run completes all eleven assertions. Native contexts
close without a sanitizer finding and preserve the existing save. Windows
Debug/Release automatic/SSE2 captures include real VM, private-desktop, worker
and simulator receipts, actual CRT providers, complete postcreation vessel
rosters and observer-off/on equivalence. `qualification.py` seals only that API
test scope; it cannot qualify the 157-scene corpus or complete Phase 6.

`Observer.cpp` reads the existing private test callbacks and public SDK during
Windows startup. It logs the real CRT mode/provider and loaded vessel identities.
Its observation can be disabled independently of CPU-mode selection, allowing
the same diagnostic DLL and math mode in both equivalence captures. It never
changes vessel state, time, input or exit behavior. Windows' existing `oapi.exit`
uses immediate CRT termination; its missing normal teardown remains an observed
property, rather than a general waiver for ordinary scene exits.

`startup-policy-v1.json` identifies only the v2 corrected script and unchanged
GeneralApiTest scenario. The native exit presents zero frames and retains the
complete initial Delta-glider row and a cleanly deleted graphics context.
`startup_contract.py` requires all eleven assertion events, the actual CPU math
lane, unchanged script/scenario bytes and preserved existing save. Eighteen
control tests reject incomplete or substituted startup evidence.

Normal stock runs opt into this variant with `--general-api-qualification FILE`.
`admission.py` makes a private asset copy and changes only the pinned script;
the canonical original remains intact. Four selected normal-host captures pass
their independent stock audits and fourteen damaged-real-evidence controls
each. The existing sixteen VesselApiTest exit controls still pass. These are
selected API captures, not full stock admission evidence.
