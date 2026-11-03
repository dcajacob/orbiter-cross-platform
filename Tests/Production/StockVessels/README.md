# Additional original Windows station observations

The native stock sweep identified seven unchanged scenarios whose declared
files are present but whose configuration-defined Mir/Wheel classes are still
rejected by the host. This fixture collects additional original Windows
observations before changing that host policy. It does not yet qualify native
Mir/Wheel support or complete Phase 6 acceptance.

`cases.json` pins the seven complete scenario files and both stations'
configuration/mesh resources to the preserved application revision
`f725194209634f7fd5d1d44d426cfa9b5e303e37`. No vessel or scenario block is removed.
The existing cockpit clocks, numerical budgets and 0.98 image-SSIM threshold
remain unchanged. Numeric dates in each stock scenario remain intact; the
observer's controlled default epoch applies only when the original application
requests its test default. This does not qualify wall-clock Today semantics.

`CockpitControls/prepare.py` stages the exact preserved application, SDK and
graphics-client binaries. Only the public SDK observation DLL is built in the
existing `ProductionCockpitDriver` test slot. The observer records every vessel
at finalized ticks 0 through 60, including background ships, SDK version,
focus eligibility, mass, inertia, cross sections, resource counts, physical
state and every docking port. It reads these values without propagation or
vessel setters. The established observer ABI, fixed clock, CRT-profile selection
and deterministic random seed follow the accepted capture workflow.

The four Windows Debug/Release automatic/SSE2 jobs execute each scenario twice,
with the locked Windows llvmpipe runtime and complete real-client rendering.
Both state/port CSVs must repeat exactly; full framebuffer repeat SSIM must
satisfy the existing threshold. Every scene must present all sixty frames and
delete its context normally. Loaded DLL hashes, original binary identities,
complete source-resource identities, runtime errors and failures are retained.
Fresh output paths are required. Existing accepted references are not rewritten.

`Gate.Test.py` removes a non-focus station and then one docking-port row at
tick 30 from separate copies of a real original capture. Both omissions must
fail while the original CSV hashes remain unchanged. This control runs after
each successful Windows capture.

Local input verification requires no Windows runtime:

```sh
python3 -B Tests/Production/StockVessels/original.py --verify-inputs
```

The standalone `original-stock-stations.yml` workflow builds the SDK observer,
captures all fourteen sessions per profile, runs the negative controls, and
retains raw artifacts on failures as well as successes. A successful reference
capture must be audited before implementing and comparing an explicitly scoped
native capability policy. Missing declared modules still cannot fall back to
configuration-defined vessels.

`verify_original.py` audits the four downloaded, hash-verified archives against
their immutable producer commit and original runtime metadata. It independently
checks every recorded artifact, all-vessel/port traces, repeated images and
Debug/Release comparisons within each CRT profile.

`native.py` builds a read-only SDK probe and captures the same seven complete
scenarios twice. The probe calls each original session phase exactly once;
its observation pacing follows the Windows producer. It records all runtime
module/library hashes and refuses changing sources or binaries. `compare.py`
requires the audited original profile and checks every physical/capability
field and port, actual camera, one-pixel projections and unmasked full-frame
SSIM with unchanged budgets. Front-facing projected objects may be outside
the viewport; the visible subset is recorded separately.

`Policy.Test.py` uses disposable hard-linked assets, unlinking changed configs
before writing. Five real startup cases must reject altered capabilities,
missing required modules, arbitrary generic clones and a wrong declared module
before any scene presentation. Source config hashes must remain unchanged.

The local Release automatic matrix now passes. The restored original base
texture lifecycle makes the DG-and-DG-S ground frame byte-identical to Windows.
See [the scoped qualification](../../../Docs/Production/StockStations.md).
Other native profiles, broader stock dependencies and sanitizer acceptance
remain separate requirements.
