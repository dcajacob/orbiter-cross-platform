# Frozen original Windows reference

Accepted on 2026-10-31 from [run 41175652054](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41175652054),
source commit `1009ee2251931ec9e120047dc41d936c216b9ed0`.
The 13 recorded numerical sources matched original upstream commit
`8e6ae437901417eef56f08b8f969ff92df83db5e` before execution.

`Orbit.csv` and `Spin.csv` contain 601 finalized-state samples at one-second
steps. `Orbit.HalfStep.csv` contains 1201 samples at half-second steps over the
same 6000-second duration. The canonical CSVs come from Windows x64 Release.
Windows Debug produced numerically identical samples; each executable's repeated
orbit and spin runs produced identical bytes.

Both full application builds and their existing tests passed. Maximum circular
position error was `1.3123027900649334e-6 m`, velocity error
`1.4881277718371488e-9 m/s`, and free-spin angular error
`4.999946986498749e-10 rad`. Energy and angular-momentum relative errors were
below `7e-15`. Half-step maximum position error fell to
`1.2411773373862428e-7 m`. All accepted budgets passed without adjustment.

`provenance.json` preserves the unmodified capture metadata, source and fixture
hashes, trace hashes, compiler/configuration information, results and original
GitHub artifact digests. `Evidence/` preserves complete original build/capture
archives beyond hosted artifact expiration, including effective runtime inputs,
commands, compiler banner, CMake settings, logs and repeated traces.

These are observations of the original Windows engine, not generated analytical
fixtures. Do not regenerate or replace them during the port. Changes require a
separate reviewed reference-capture decision. The acceptance commit is the Git
commit introducing this directory; the capture source commit above stays fixed.
