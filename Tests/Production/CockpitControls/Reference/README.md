# Accepted original Windows cockpit control references

Accepted run: [41482729373](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41482729373).
Producer source: `6e936b04f09da58b8e67e41521375ecc77db7ab8`.
Application/SDK: exact archived `f725194209634f7fd5d1d44d426cfa9b5e303e37`.
OpenGL client: exact archived original reference from `68400a7d3750240afb53890e1da2306c71f6380e`.

Five cases cover real generic/DG/DG-S RCS mode controls through the owned Windows
render-window procedure and the original 2D/VC hit testing. Each ran twice in
Debug and Release. Inputs, states, text, geometry, atlas updates and application
lifecycle observations repeat exactly. Original numeric differences between
configurations are zero; full-frame and direct MFD image SSIM is 1.0. The actual
vessel changes from rotational to linear RCS mode after recorded tick 10 and
returns after tick 30. These are selector tests, with no thruster input.

The archived ZIP digests were independently verified and the Debug/Release
comparison rerun locally before acceptance. `provenance.json` locks 992 canonical
file hashes and the producer inputs/source. Existing orbital/propellant/image
budgets and the earlier nine-case reference remain unchanged. No reference is
regenerated automatically, and staging refuses to replace an existing output.

Storage: [production-windows-cockpit-controls-v1](https://github.com/dcajacob/orbiter-cross-platform/releases/tag/production-windows-cockpit-controls-v1).
The original application/SDK/client runtime archives remain in the parent
[production-windows-cockpit-v1](https://github.com/dcajacob/orbiter-cross-platform/releases/tag/production-windows-cockpit-v1).

Verify checkout inputs/source with `python3 -B Tests/Production/CockpitControls/frozen_controls.py`.
Stage canonical files using `--cache <directory> --output <new-directory>`;
`--offline` permits verified cached archives only. These references establish
original control behavior. They do not establish native cockpit operation,
coverage of every cockpit control, or a stock-playable release.
