# Accepted native headless parity evidence

Accepted on 2026-10-31 from [run 41177834521](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41177834521),
tested source `6f79da173ee016fa693966026d68bcf22831bb12`. All eight jobs passed.
The final documentation/evidence commit changes no numerical source.

| Hosted check | Result |
| --- | --- |
| Native Ubuntu 24.04/GCC x64 Debug and Release | 8/8 CTest suites per build |
| Native Windows 2022/MSVC x64 Debug and Release | 8/8 CTest suites per build |
| Native four-build comparison | All parsed numerical samples identical |
| Full Windows application Debug and Release | Builds, 2/2 existing suites, reference checks passed |
| Application Debug/Release comparison | Zero numerical error |

Every default orbit/spin run has 601 samples over 6000 seconds; half-step runs
have 1201 samples over the same duration. Same-executable orbit and spin repeats
match byte-for-byte. Analytical checks, invariants and half-step convergence pass.
Native/reference position error is at most `1.2013700229374393e-7 m` across all
three cases, velocity error at most `8.866990313695243e-11 m/s`; rotation, angular
velocity and MJD errors are zero. Both current Windows applications reproduce
all original traces numerically exactly. The original budgets remain unchanged.

`native-parity.json` and `application-{Debug,Release}.json` are readable copies
of hosted reports. `provenance.json` records source/reference commits, all job
results, GitHub artifact IDs/digests and the supplemental job-log archive digest.
`Evidence/` contains the eight exact downloaded GitHub artifact ZIPs, plus all
eight decoded job logs in `workflow-job-logs.zip`. All archive digests were
verified locally. The archived CSVs were reloaded and comparisons/invariants
independently reproduced locally from the downloaded evidence. Reports and
archives remain available after GitHub's 14-day retention period.

The [original reference](../Reference/README.md) remains separate and immutable.
These acceptance outputs do not replace or refresh it.

Local Linux results are separate: GCC 15.2, CMake 4.2.3, Debug/Release 8/8 suites.
`Local/` preserves their parity reports and final CTest logs. Local runner
position analytical error is `1.4143184329290157e-6 m`, falling to
`1.1808439414391757e-7 m` with half steps; energy/angular-momentum relative drift
stays below `7e-15`. Local Linux success alone did not establish hosted parity.

See [the build/run instructions and limitations](../README.md). This milestone
covers one fixed spherical primary and one generic unpowered vessel; it does
not establish general scenario compatibility or a graphical Linux application.
