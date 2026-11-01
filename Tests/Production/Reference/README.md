# Frozen production Windows orbit / propulsion reference

Accepted source `e70041fa2991d1bfefe66575ced1e32c92898f82`,
[hosted run 41187217665](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41187217665).
The production implementation remains the frozen pre-extraction revision
`38b7c627878ea893390675616897071f8bb8e90f`; only test infrastructure was added.

Both MSVC x64 Debug and Release execute the production Sol/SPICE world with stock
ISS and source-built ShuttlePB. Each orbit / main-engine-and-RCS case is repeated
twice. Each case's pair of runs is byte-identical in each configuration. Every
sample agrees exactly between Debug and Release under the unchanged budgets.
There are 601 samples per object over 6,000 recorded seconds; five objects are
observed. Each run records 30,006 driver/control/lifecycle events. The controlled
case consumes 18.048 kg (final fuel 731.9520000000034 kg), matching the independent
thrust/ISP/tick calculation within the declared quantity budget.

Actual mesh/class/thruster/propellant identities include
`ISS,ProjectAlpha_ISS,1,18,1` and `PB,ShuttlePB,1,16,1`. This is CPU object/resource
evidence, not evidence of a rendered scene or working graphics client.

[provenance.json](provenance.json) freezes the fixture/data identities, observed
field coverage, budgets, original artifact ZIP hashes and individual trace hashes.
Full source/toolchain/SDK/dependency/module metadata, invocation/input hashes,
traces, original logs and saved scenarios remain in the unchanged original ZIPs:

- [Debug evidence](../Verification/Evidence/41187217665-production-reference-Debug-x64.zip)
- [Release evidence](../Verification/Evidence/41187217665-production-reference-Release-x64.zip)
- [Comparison](../Verification/Evidence/41187217665-production-reference-comparison.zip)

```sh
python3 -B Tests/Production/frozen_reference.py
python3 -B Tests/Production/frozen_reference.py --candidate /path/to/current/production-reference
```

Normal CI uses `capture_reference.py --reference Tests/Production/Reference`:
the current application may change, but its new output must match the frozen
evidence. Verification does not rewrite this directory or its archives. Fresh
baseline capture without `--reference` still requires the original production
implementation. There is no automatic acceptance or refresh command.

The existing two-body reference is separate and unchanged. These production
references cover only the two declared reduced cases. They do not establish
terrain/contact/docking, atmosphere, all RCS/autopilot modes, clock/lifetime
transitions, save/reload precision, vessel callback ordering or graphics/cockpit
acceptance. Capture those cases before extracting their affected subsystems.

## Atmosphere profile discovered during the native vessel extraction

The immutable logs in this early capture report missing `EarthAtmJ71G.dll` and
`MarsAtm2006.dll`: its build-tree staging did not reproduce the atmosphere
modules' body-specific install directories. These traces retain that original
fallback atmosphere profile. They are unchanged and still protect that Windows
profile; they must not be used to disable correctly installed native forces.

The later, pre-extraction [behavior references](../BehaviorReference/README.md)
from run `41193020450` explicitly stage the source-built atmosphere DLLs at their
CMake install destinations. Their RCS, autopilot and callback-fixture numerical
states are the matching references for native vessels with the actual J71G
module. The native component verifier checks initial nonzero density and retains
all original numerical budgets. A matching, correctly staged long-duration
Windows/native comparison is still required for the 6,000-step production runs.
