# Pre-flight Windows references

Accepted from [run 41350187262](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41350187262),
using the complete, digest-verified Windows application/SDK built at
`391919027ac3e4a4d42f145373c788fc859c32cd`, with the controls/observation driver
at `a72fabef7bae160580d76bcf7aa25960d715e824`. Capture predates native flight
integration. No physics, stock modules or serializers were replaced.

Both MSVC configurations run each case twice with byte-identical numerical and
event traces; the Debug/Release comparison passes with zero measured differences.
The cases cover main/hover thrust, single-step manual requests for all twelve
RCS groups, five orbital autopilot modes, and ShuttlePB save/reload using the
original stock serializer. The broader existing frozen references retain docking,
contact, clock/pause and other behavior coverage unchanged.

`provenance.json` records the original GitHub ZIP hashes and the unchanged
orbital/propulsion budgets. The ZIPs preserve control/observation CSVs, saved
scenarios, runtime metadata and logs; they contain no application binaries or
stock data packages. Native reload comparisons use the Windows round-trip state,
including the stock format's existing decimal quantization.

The capture workflow is manual-only after acceptance. Neither native test runs
nor hosted regression checks overwrite these references. The failed initial
capture (41349328398) is not accepted: its validator assumed a Delta-glider for
every reload and rejected the otherwise completed ShuttlePB case.
