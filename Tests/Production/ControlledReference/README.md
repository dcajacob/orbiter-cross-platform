# Additional frozen original Windows controlled landing

[Run 41374941546](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41374941546)
qualifies 6,000 original production steps at 60 Hz in MSVC Debug and Release.
Each executable repeats its numerical traces byte-identically, and the two
configurations pass the existing contact/orbital comparison limits.

The real ShuttlePB rises above 10.67 m above Edwards terrain, returns at at most
0.682 m/s, remains within 3.95 degrees of upright, and reaches the actual SDK
landed state. It uses the existing horizon and hover-altitude programs and
shuts both down before the final unpowered settling period. The physical safety
criteria were declared before capture. No production force formula changed.

These are additional references. The older uncontrolled-impact capture and its
native attitude failure remain preserved in `GroundReference`; that capture ends
inverted and cannot establish safe landing support. No old reference, threshold
or failing result was replaced by these files.

`provenance.json` records the frozen application's source and binary manifest,
controller revision, input hashes, original hosted artifact IDs/hashes, and
every retained archive member. The canonical archives are lossless repackings:
only duplicate repeat directories were removed after byte-identical checks.
Numerical trace bytes remain untouched. The capture workflow is manual-only.

Verify with `python3 -B Tests/Production/ControlledLanding/frozen.py`.
