# Original legacy station observations

This additional reference fixture measures four complete unchanged stock scenes
that use the configuration-defined `ISS` class. `DG dumbbell` also contains three
original `Module1` vessels. Every declared vessel remains present. No native
class is admitted by adding this fixture.

The original Windows application, SDK and graphics client remain at
`f725194209634f7fd5d1d44d426cfa9b5e303e37`. Only the already established read-only
public SDK observer is rebuilt. The existing 60-frame, 0.25-second clock,
numerical budgets and full-frame image threshold remain unchanged. Each scene
runs twice in each Debug/Release automatic/SSE2 profile. Captures retain all
61 finalized states for every vessel and every docking port, capability data,
actual loaded modules and math implementation, camera, full framebuffer and
normal graphics teardown.

The scenario, ISS/Module1 configuration and mesh hashes are checked against the
original source. The staged raw scenario hash is recorded before execution and
rechecked alongside its frozen LF identity. The entire preserved package and
observer sources must remain unchanged. A capture remains explicitly awaiting
an independent four-profile audit; green capture jobs alone do not qualify a
native capability policy or complete Phase 6.

`Gate.Test.py` uses the complete dumbbell capture, including all three Module1
objects, to reject twelve damaged copies. Missing background objects, ports or
ticks, duplicate ports, altered capabilities, nonfinite state, shifted time,
changed scenario bytes or line endings, incomplete teardown and a wrong renderer
must fail while the original remains unchanged.

```sh
python3 -B Tests/Production/LegacyStations/original.py --verify-inputs
```

Actual captures require native Windows/MSVC and the preserved SDK/runtime staged
by `CockpitControls/prepare.py`. Use fresh outputs; never rebuild an accepted
application or SDK to produce a new reference.
