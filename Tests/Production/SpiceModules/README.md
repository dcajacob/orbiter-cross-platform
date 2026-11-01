# Production celestial module reference and native port

The actual production `SPICE/spice.cpp` now builds as a native module linked to
the same shared engine library and internal SDK as its host. Earth J71G, Earth
2006 and Mars 2006 atmosphere modules use their original production sources.
Native interfaces use explicit production body, clock, configuration and indexed
resource services. They contain no Win32 API emulation. Windows legacy module
entry points, public SDK declarations and class layouts remain unchanged.

Hosted native execution now passes Windows MSVC and Linux GCC x64 Debug and
Release in [run 41291123424](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41291123424),
source `b165fc21`. All four builds produce repeated traces byte-identical to
the original Windows application reference. [Preserved evidence](Verification/provenance.json)
retains compiler/build output, actual binary/module/data hashes and comparison
reports; identical trace bytes refer to their existing frozen ZIP member.
Verify this evidence offline with
`python3 -B Tests/Production/SpiceModules/Verification/verify.py`.

The original Windows reference was captured before modifying these sources,
using the accepted application/SDK from source `2e8bbbf2`. Hosted run
[41289480046](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41289480046)
passes Debug and Release with byte-identical repeats and zero disagreement
between configurations. The locked schedule covers 41 real modules, 129 stock
scenario epochs, 6,001 forward interpolation calls per request profile and
recorded nonmonotonic time queries: 25,092 sampled rows per executable.

The observer respects returned flags, zeros unreturned blocks, and records
out-of-bracket resets between request masks because the original interpolation
cache is time-keyed. The Sun's barycentric-only request may return no data.
Three early preparation attempts exposed DLL staging and observer assumptions;
they are not accepted numerical runs. Linked CI artifacts retain those failures.
No production numerical formula or acceptance budget was changed to pass.

`Reference/` preserves original artifact ZIPs, per-member hashes, exact source,
compiler output, runtime identity and traces. Windows initially checked out
this new nested JSON with CRLF. The provenance preserves that actual recorded
hash and separately locks/reconstructs identical LF contents. This administrative
metadata correction changed no trace, protocol content or budget. New checkouts
use explicit LF. Verification is read-only:

```sh
python3 -B Tests/Production/SpiceModules/frozen_reference.py
python3 -B Tests/Production/SpiceModules/source_audit.py
```

Native lifecycle uses the checked C bootstrap, then actual C++ module instances.
The celestial context remains alive until shutdown. Atmospheres are destroyed
before their parent module; the last SPICE instance closes the kernel pool before
unloading. Required missing modules, incompatible SDKs, missing/ambiguous assets
and invalid configuration fail explicitly. Kernel resolution uses explicit roots;
native SPICE diagnostics do not create files in the working directory.

```sh
cmake -S Src/Orbiter/Production -B out/celestial \
  -DCMAKE_BUILD_TYPE=Release -DORBITER_BUILD_NATIVE_CELESTIAL_MODULES=ON
cmake --build out/celestial --target production_native_spice_observer -j2
python3 -B Tests/Production/SpiceModules/verify_port.py \
  --executable out/celestial/production_native_spice_observer \
  --modules out/celestial/NativeModules --data /path/to/verified/stock/data \
  --output out/native-spice-verification --configuration Release
```

Append `.exe` on Windows. The native-module matrix runs this on Linux GCC and
Windows MSVC x64 Debug/Release, then compares all four builds with each other and
the frozen Windows evidence. Position/velocity budgets stay 0.01 m and 1e-5 m/s;
query identities, times and response flags are exact. Each native run repeats.
The original full application/behavior and Windows OpenGL gates remain separate.

Local Linux Debug/Release and strict ASan/UBSan/LeakSanitizer observations pass
with zero state disagreement, alongside the existing fourteen boundary checks.
This is direct module verification using actual production `CelestialBody`
configuration, not an authoritative `PlanetarySystem`, `Planet`, `Vessel` or
`Camera` session. It cannot satisfy the requested native textured-scene gate.
