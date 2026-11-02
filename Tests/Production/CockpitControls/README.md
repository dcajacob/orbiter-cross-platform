# Original Windows cockpit control references

This gate exercises actual render-window mouse routing, the original Pane hit
testing, and real generic/DG/DG-S RCS mode controls before native cockpit input
extraction. It is not native cockpit or stock-release acceptance.

The producer reuses the exact application/SDK and OpenGL client binaries from
`production-windows-cockpit-v1`. Archive and per-file hashes are verified before
staging; no extracted production code is used to create a reference. Only the
additional SDK observation/control plugin is rebuilt. Existing nine-case
cockpit references, producer files and numerical/image budgets are unchanged.

Five cases cover generic glass instruments, DG and DG-S 2D panels, and DG and
DG-S virtual cockpits. Four tick-indexed button events select linear RCS mode
and then restore rotational mode. VC events project a point inside the stock
RCS dial's declared click quadrilateral, then pass actual pixel coordinates
through the owned Windows render-window procedure. The driver does not call a
vessel mouse callback or set RCS mode directly. RCS mode selection persists;
these cases apply no thruster input. Momentary thrust/release remains covered
by the Phase 5 keyboard suite.

Each case runs twice in fresh Windows processes for 60 quarter-second ticks.
Require exact input, finalized numerical, displayed-text and geometry repeats;
verify the vessel's actual mode at every sample. Use the existing orbital,
propellant, one-pixel and SSIM budgets for Debug/Release comparisons. Actual
desktop/viewport dimensions and loaded application/client/Mesa/stock assets are
recorded. A failed case blocks native input extraction; its output is diagnostic
and cannot be frozen as a reference.

The dedicated workflow performs the complete capture and comparison. On an
MSVC x64 command prompt, with the existing verified data and Mesa directories:

```text
python -B Tests/Production/CockpitControls/prepare.py --configuration Debug --cache out/cockpit-cache --output out/original-app
cmake -S Tests/Production/CockpitControls -B out/control-driver -G Ninja -DCMAKE_BUILD_TYPE=Debug -DORBITER_TEST_RUNTIME=<absolute-path-to-out/original-app>
cmake --build out/control-driver --parallel 2
python -B Tests/Production/CockpitControls/capture.py --orbiter out/original-app/Orbiter.exe --data out/data --planets out/planets --mesa out/mesa --configuration Debug --output out/control-reference
```

`prepare.py --offline` verifies cached original archives without downloading.
All staging/capture outputs refuse replacement. Once both configurations and
the comparison pass, preserve provenance, inputs, logs, traces and original
captures separately and switch the reference workflow to manual-only. Do not
automatically refresh an accepted reference.

The five original cases are now accepted in run 41482729373. Their immutable
provenance, hashes and comparison are in `Reference/`. The capture workflow is
manual-only; preservation uses a separate workflow. Native input extraction
must compare against these files rather than recapturing the reference.

Current regression entry points are separate from the frozen producer:

- `current.py` rebuilds the original observation driver against the current
  Windows SDK and compares all five cases with the staged originals. The normal
  Windows client workflow runs it after the nine instrument cases.
- `native.py` compares the supported generic glass case using the same real
  Pane hit testing and frozen tick/coordinate schedule. Native DG/DG-S panels
  and virtual cockpits remain unsupported.
- `mouse_smoke.py` separately verifies actual GLFW/X11 input delivery, RCS mode
  switches, momentary keyboard thrust and focus-loss release, plus the original
  MFD power and Surface/Orbit selection buttons. It operates only on the window
  owned by its child test process. This test is not a frozen numerical replay.

Stage accepted references with `frozen_controls.py --cache <cache> --output
<frozen>` (add `--offline` to require verified cached archives). Native scripts
take `--executable`, `--assets`, `--data`, `--modules`, `--planets`, and `--output`;
the deterministic comparison additionally takes `--frozen` and
`--configuration Debug|Release`. Run on an owned X11 display or `xvfb-run`, with
`LIBGL_ALWAYS_SOFTWARE=1 GALLIUM_DRIVER=llvmpipe`. The native workflow runs both
checks on all four Debug/Release automatic/SSE2 profiles and archives evidence.
These engineering checks do not establish complete native cockpit compatibility.
