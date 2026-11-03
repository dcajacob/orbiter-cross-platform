# Windows CRT dispatch diagnostic

The original atmospheric DG AAP capture first diverges at tick 34 when the
Debug and Release CRTs evaluate the same arcsine input. The direct CRT exports
also differ, even on one host with FMA3 enabled in both runtimes. This probe
isolates the installed runtime from simulator code and compiler optimization.

Run in an x64 Visual Studio developer shell:

```powershell
python -B Tests/Production/CrtDiagnostic/capture.py --output out/crt-diagnostic
```

The workflow runs both builds on each Windows Server 2022 and 2025 host. It
uses each image's installed Visual Studio (the 2025 runner now supplies 2026),
and records the compiler rather than assuming both images carry VS 2022. It
records the actual export owner, file/product versions, SHA256, compiler,
CPU, rounding state and FMA3 state. A fixed corpus includes the exact recorded
input, its neighbours, endpoints, signed zero, subnormals and a uniform grid.
Every profile repeats in a fresh process. Default dispatch is observed before
separate SSE2 and FMA3 requests. Each linked call is checked against its direct
CRT export.

Installed SDK Debug and redistributable Release CRTs are also requested by
absolute path in fresh Release processes. Their own FMA3 controls and arcsine
exports are used. The report distinguishes the requested DLL from the actual
loaded provider; it does not assume that requesting a DLL overrides Windows
loader policy. Linked results in these SDK probes still belong to the process's
Release CRT and are labelled separately. No SDK DLL is copied or uploaded.

An `observed` report means the capture is valid, not that the builds agree.
Differences are reported without a tolerance or an acceptance override. This
workflow does not change the preserved application, frozen references, native
math dispatch or the original Windows Lua/AAP cross-build gate. Full simulator
qualification remains necessary after any runtime provisioning change.

Microsoft documents that the Release UCRT is an operating-system component
and that modern Windows uses its system copy even when a newer application-local
copy is present: [Universal CRT deployment](https://learn.microsoft.com/en-us/cpp/windows/universal-crt-deployment).
The diagnostic measures the actual providers instead of inferring them from
the installed compiler or SDK version.

## First Windows Server 2022 capture

[Run 41587424541](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41587424541)
captured Debug product version `10.0.26100.7705` and Release product version
`10.0.20348.5756`. Their hashes match the providers recorded in the original
simulator's paired run. With default dispatch, 115 of 8,517 inputs differ by
one ULP; the forced-SSE2 captures agree throughout. Both the Debug and Release
SDK `10.0.26100.7705` exports return the newer result for the flight's critical
input, while the older installed SDK versions return the system Release result.
This demonstrates a runtime-version difference, rather than an intrinsic
Debug-versus-Release compiler difference. It does not prove full-flight parity.

[Run 41587772339](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41587772339)
then observed Windows Server 2025 Debug product version `10.0.26100.9457` and
Release product version `10.0.26100.33648`. All 8,517 outputs agree across builds
in default, SSE2 and explicitly enabled FMA3 profiles. The full original Lua/AAP
workflow now compares both OS hosts with its existing exact gate.
