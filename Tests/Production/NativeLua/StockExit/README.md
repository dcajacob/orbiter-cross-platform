# Unchanged stock script exit observation

This fixture observes `Tests/VesselApiTest.scn` and its unmodified script at
the preserved Windows application/SDK/client source
`f725194209634f7fd5d1d44d426cfa9b5e303e37`. It rebuilds only an observation DLL.
It also observes native builds through the same public SDK fields at existing
session boundaries, without dispatching inputs or changing propagation calls.

Each scenario retains all eight original vessels. The reader requires the
complete ordered script log: 60 events and 28 assertion-pass records derived
from the pinned script bytes. It checks the real exit code, a contiguous
all-vessel trace and every docking port at every completed tick. Captures run
twice, with byte-identical repeated traces. Native captures additionally require
matching presentations, context deletion and an unchanged existing save file.
Actual build configuration, math selection and sanitizer linkage are checked.

The four original Debug/Release and automatic/SSE2 profiles establish the
termination point independently of the native repair. Their observations must
be audited and pinned before the stock-corpus harness gains an intentional-exit
policy. This fixture currently changes no stock-corpus acceptance rule. All
ordinary scenarios retain their sixty-frame requirement; a missing dependency,
failed assertion, partial trace or early shutdown cannot become a pass.

`Gate.Test.py` damages copied real captures in ten ways, including a missing
background ship, docking port or final tick, a forged completion log, a changed
scenario and an incorrect exit code. The owning capture remains unchanged.

Original captures require native Windows and the preserved runtime staged by
`CockpitControls/prepare.py`. Native captures use a matching existing engine
and renderer build. `--dependencies` starts an owned private Wayland compositor;
omit it under an owned X11 display, such as `xvfb-run`. Instrumented runs require
`--sanitize` and the qualified private dependency directories. Use fresh outputs
and never rebuild retained packages.
