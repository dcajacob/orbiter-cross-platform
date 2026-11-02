# Accepted original Windows ground-flight reference

[Run 41368023101](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41368023101)
passes seven real ShuttlePB cases in MSVC Debug and Release, with byte-identical
repeats and a passing hosted cross-configuration comparison. It uses the preserved
application/SDK at `391919027ac3e4a4d42f145373c788fc859c32cd` and observation/control
driver at the full revision recorded in `provenance.json` (`1c930be8`). No native
ground-path changes preceded acceptance.

Cases cover real Edwards elevation, atmospheric flight, elevator/aileron inputs
and animations without RCS fuel use, unpowered contact, completed takeoff/landing,
landed save and reload. The takeoff case must reach SDK status 1 and serialize as
`STATUS Landed Earth`; contact alone is insufficient. All use the application's
normal 1/60-second tick. Their contact/propulsion budgets and the ISS's unchanged
orbital budgets are declared in the locked input manifest.

The canonical ZIP/LZMA files contain unchanged bytes from the original artifacts.
Duplicate repeat traces are represented by verified identical SHA256s; first-run
traces, configurations, scenarios, reports, compiler settings and build logs are
retained. Per-member hashes and original artifact hashes/links preserve that
provenance. Only source-file hash checking normalizes Windows CRLF to LF. Trace
contents are never normalized, synthesized or regenerated. The original full
archives also remain in the local production cache and hosted run artifacts.

```sh
python3 -B Tests/Production/GroundFlight/frozen.py
```

The capture workflow is now manual-only. Native CI reads these immutable files;
it cannot refresh them. Earlier rejected candidates and harness errors are
recorded in [DIAGNOSTICS.md](../GroundFlight/DIAGNOSTICS.md). Existing two-body,
production, orbital-flight and image references remain unchanged.
