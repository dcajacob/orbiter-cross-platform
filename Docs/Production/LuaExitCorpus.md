# Complete stock sweep after the Transfer MFD and Lua-exit repairs

The fresh instrumented sweep attempted all **157 unchanged stock scenarios** at
runtime source `b1e3f1d60485149f5df63b5e89b531cb8ed0d8cf`, using observer
`a6feea8a2898d8dd66c950316fc4fc80321ccd8a`. The independent audit confirms
**114 passed and 43 failed**. The preceding 112/45 raw result remains preserved.
Exactly two outcomes improved: `Navigation/Lunar transfer/Lunar transfer 1.scn`
and `Tests/VesselApiTest.scn`. Every other scenario kept its previous outcome.

The run recorded 6,853 presentations, 32,503 finite all-vessel state rows and
157 completed graphics-context deletions. All processes returned zero or one;
there were no signals or AddressSanitizer, UndefinedBehaviorSanitizer or
LeakSanitizer diagnostics. Both engine C and C++ sources were instrumented,
with explicit leak detection, no suppressions and the qualified private
Fontconfig, Mesa and GDK dependencies. All protected sources, runtime files,
observer inputs and reference pins remained unchanged during the sweep.

Ordinary passing scenes retain all sixty 0.25-second frames and complete
declared vessel manifests. The one audited intentional-exit case retains the
unchanged stock scenario and script, all eight vessels, thirteen presentations,
fourteen finalized snapshots, 112 SDK vessel rows and 210 docking-port rows.
All 60 ordered log events and 28 assertion-pass records are present. Its real
exit code is zero, the context is deleted and the existing save remains
unchanged. Every numerical error against its original Windows profile is zero.

The remaining failures are explicit:

| Cause | Scenarios |
| --- | ---: |
| Missing declared native dependencies | 38 |
| Legacy ISS/Module1 native capabilities awaiting qualification | 4 |
| Preserved original GeneralApiTest Earth-obliquity assertion | 1 |

GeneralApiTest completes sixty presentations and returns zero while logging its
failed Lua assertion; the assertion keeps that scenario failed. The other 42
failures return one with clean context deletion. Dependency rejection does not
qualify a missing module. The [legacy station reference](../../Tests/Production/LegacyStations/README.md)
now has audited original observations, while native admission and comparisons
remain separate work.

Sixteen damaged-evidence exit-policy controls, the non-focus-vessel removal
control and the inventory controls pass against this fresh complete capture.
The frozen source lock and every original scenario byte remain unchanged.
The seven historical lock-inventory parsing discrepancies remain recorded.

[The machine record](LuaExitCorpusVerification.json) identifies every failure,
the two changed outcomes, source/build identities, controls and archive pins.
The local bundle is `out/phase6-stock-exit-complete-corpus-evidence-v1.tar.gz`:
23,115,880 bytes, 5,100 members, SHA-256
`49dadf0c44bf458fd425de8d79555ee9ee6149449299092817d9a2e6c0f0f744`.
All archived payload hashes were rechecked. It contains raw attempts, both
audits, original stock-exit references, controls and source snapshots; matching
runtime packages are identified by the preceding Lua process-exit bundle.
Font and asset collections are excluded. Remote preservation of the complete
native bundle remains open.

This is complete initialization/smoke coverage with retained failures. Required
modules, native legacy-station qualification, the preserved assertion, current
hosted comparison, final hardware/input gates and complete Phase 6 acceptance
remain open. The user has no physical controller available; that gate remains
unverified.
