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

The shared reader's current verification command is separate from historical
capture and never writes `Reference/`:

```sh
cmake -S Src/Orbiter/Production -B out/archive-core -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build out/archive-core
ctest --test-dir out/archive-core --output-on-failure
python3 -B Tests/Production/Archives/verify_port.py \
  --executable out/archive-core/tests/production_archive_observer \
  --data /path/to/verified/data --output out/archive-verification --configuration Release
```

On Windows append `.exe` to the observer filename. Linux needs native zlib
development headers >=1.2.11 when building; its runtime uses the OS zlib library.
Windows builds link the original pinned zlib source. The normal CTest cases use
generated fixtures only and do not download planetary assets. Full archive jobs
run the locked 28-file data profile on Windows/Linux Debug/Release and require
exact agreement between all four builds and original Windows.

The engine reader validates disk extents, roots, child indices/cycles, payload
sizes and stream/decompression failures. It retains the existing factory's null
failure result and exposes an internal diagnostic with `Error()`. Invalid tile
coordinates and missing tiles return no data; output pointers are cleared.
Seventy failure/resource cases cover truncated headers, unsupported headers,
invalid graph/offsets, corrupt/trailing compressed input and truncation after
opening. Repeated real reader load/decode/unload and explicit header round trips
are checked. These reader lifetimes do not count as graphical world sessions.
