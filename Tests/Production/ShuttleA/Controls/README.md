# Shuttle-A keyboard and persistence observations

This additional fixture starts from the **unchanged** `Shuttle-A/ISS Approach.scn`,
including all six vessels. It uses K, O, Ctrl+O and G through ordinary input
dispatch to operate the docking hatch, both airlocks and landing gear. The VC
case first sends the ordinary F8 command. It does not invoke vessel input
callbacks or mechanism setters directly.

Each cockpit runs twice. Each repetition saves and starts a fresh process at
four checkpoints: moving (16 ticks), resumed without further input (96),
returning to the original endpoints (112), and restored endpoints (4). Every
tick is 0.25 seconds. The matrix contains sixteen processes and 912 successful
presents. All vessels, docking ports, attachment ports, six focus animations and
cockpit selection are observed at initialization and every finalized tick.

The Windows driver builds against the preserved application/SDK/client from
`f725194209634f7fd5d1d44d426cfa9b5e303e37`; it replaces only the observation
plugin. `.github/workflows/original-shuttle-a-controls.yml` captures Debug and
Release with automatic and explicit SSE2 CRT selection. Existing accepted
references are never overwritten or refreshed by this workflow.

Verify the input scenario without running a session:

```sh
python3 -B Tests/Production/ShuttleA/Controls/capture.py --verify-inputs
```

Capture the native runtime in an owned display, using the matching build's
library path and software OpenGL environment:

```sh
python3 -B Tests/Production/ShuttleA/Controls/capture.py \
  --executable out/native-cockpit-engine/orbiter-production \
  --assets out/scene-resources --data out/data --planets out/planets \
  --configuration Release --math-profile automatic \
  --runtime-source-commit FULL_BUILD_COMMIT --output out/native-shuttle-a-controls
```

Output directories must be new. A successful capture checks the requested
behavior and deterministic repeats. Windows/native parity additionally requires
the four-profile artifact audit and `compare.py`; a native capture alone does
not qualify parity. Full-frame comparisons in the longer phases retain the
existing stock-scene SSIM and numerical budgets. Mouse controls, pod operation,
payload deployment/reload, the editor, physical-controller input and overall
Phase 6 acceptance remain separate work.
