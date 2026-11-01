# Planetary archive extraction gate

The original `ZTreeMgr` still supplies the Windows application. Before replacing
its Win32 types, native structure reads and file seeking, capture both hosted
Windows configurations with the unchanged production source. `protocol.json`
locks the source, observer, independent decoder and standard data profile.
No accepted reference is regenerated automatically.

The test observes all table-of-contents records and forty tile queries for each
of the 28 publisher archives. Queries cover levels 1–12, both hemispheres, polar
corners and first/middle/last records. Two generated fixtures exercise every
child quadrant, empty parent records, nonzero node padding and a sparse payload
offset beyond four GiB. Each run must exactly match an independent interpretation
of the 48-byte little-endian header, 32-byte disk nodes and decoded zlib bytes.
There are no numerical tolerances for this gate.

The capture runs twice per archive and preserves canonical payload hashes,
indices, compressed/inflated sizes, full table hashes, input identities, source,
executable hash, host, compiler/build logs and protocol identity. Decoded visual
assets are temporary and are excluded from reference Git history. The verified
publisher packages remain the reproducible input source.

```powershell
python Tests/Production/Archives/observations.py `
  --executable out/production-app/production_archive_observer.exe `
  --data out/standard-planets --output out/production-archives `
  --configuration Release
```

This is an archive reader gate, not native terrain, contact or world acceptance.
The existing frozen production behavior/contact references remain required.
The original Windows capture from source `ba323026` is explicitly accepted in
`Reference/`: hosted run
[41286317998](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41286317998)
passed Debug and Release, two exact decodes per archive. Both configurations
agree exactly and match the independent decoder, including sparse 64-bit
seeking. The raw artifact ZIPs retain compiler/build logs and observation
manifests with per-member hashes. Verify them without network or reference edits:

```sh
python3 -B Tests/Production/Archives/frozen_reference.py
```

Subsequent extraction must compare against this accepted evidence. The original
capture command rejects changed production source and cannot refresh it.
