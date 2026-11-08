# Hosted closeout builds

`phase6-hosted-closeout.yml` runs on the dedicated
`qualification/hosted-closeout` branch. It checks every discovered closeout
control, reuses the complete existing Windows application/client workflow, and
builds the full native stock packages in Debug/Release and automatic/SSE2.
The existing qualification campaign can continue its native runtime and original
Windows captures while this distinct build scope runs. This branch does not
trigger a duplicate portable or full qualification campaign.
The `qualification/windows-client-retry` branch runs the same Windows checks and
helper controls while leaving the already-running full native package builds
alone. CMake's dotted policy value is quoted as one native argument in PowerShell.

The native package job invokes the existing `RemainingVessels/build_native.py`
with `--sanitizers --include-unit-tests` and the unchanged dependency pins.
It builds the normal host, all stock families, both retained diagnostic hosts,
registered engine units, and unchanged upstream C++/Lua unit bodies. It executes
the complete registered test inventories, discovers actual upstream Catch cases,
and retains source-bound binaries, generated sources and real test results.
Loading ASan before the Python math probe permits instrumented shared-library
loading without disabling address, leak or undefined-behavior diagnostics.
Python uses `PYTHONMALLOC=malloc` in these instrumented launches so its object
allocator participates in the same allocation tracking. A separate launcher
control loads a native library into Python, requires the clean path to pass,
and requires an actual 4096-byte native leak to fail. Intentional invalid native
array indices must also fail. These small controls precede the full builds.
The system CPython 3.12 still retains allocations during the clean native-library
load even with the system allocator. The instrumented harness explicitly selects
the runner's cached CPython 3.14 and binds CMake's test interpreter to that same
executable. The native leak control must still fail; no suppression is added.

The first GCC 13 full-stock units exposed the array-indexed member-pointer
miscompilation described in [GCC PR116449](https://gcc.gnu.org/pipermail/gcc-bugs/2024-September/879559.html).
Rigid-body dispatch now captures the exact same selected member pointer before
calling it. `CompilerDispatch.Test.py` reverses only that two-line spelling and
requires every remaining runtime byte and every original free-spin test byte to
match the prior source. No force formula, integrator, arguments, stage order,
step count or numerical tolerance changes. The native-only retry branch runs
the full four-profile sanitizer matrix while preserving active Windows jobs.
Both engine and upstream unit inventories run even if the other fails. Failed
or incomplete units keep the job failed; completed runtime binaries, generated
sources and raw failure logs are still sealed with an explicitly unqualified
status for diagnosis. Package retention cannot convert a failed test into a pass.

The CCC package jobs passed all 32 engine CTest processes and both unchanged
upstream C++/Lua processes, then failed the separate Lua case-discovery command:
the custom unit main requires its resource directory before Catch options.
The corrected build workflow supplies that existing asset directory.
`phase6-native-discovery-recheck.yml` avoids rebuilding those completed binaries.
It downloads the original API-bound ZIP, verifies its digest and every sealed
member, preserves the original failed receipt, and independently re-reads the
passed unit XML against the complete registered inventories. It executes fresh
discovery and both complete upstream units from the unchanged retained binaries.
Every discovered/executed case must match the immutable upstream source name,
tags and source line. Reports distinguish compiled producer CCC from the new
collector and retain the original raw ZIP. This is an explicit evidence
correction, not a relabelled original job or final qualification.

The Windows 2025 runner's CMake 4 requires the explicit external setting
`CMAKE_POLICY_VERSION_MINIMUM=3.5` for the unchanged pinned zlib source. This is
the same compatibility setting already used by the renderer configuration;
every other application build/test option and existing simulation command stays
intact. `HostedCampaign.Test.py` checks these exact allowed setup differences.

Successful package retention means **built and unit tested only**. Full stock
writer/reload captures, independent cross-cohort audits, class admission and
the final candidate remain separate. Existing failed and interrupted local
attempts are retained. No capture is relabelled as a different source revision.

All jobs use standard `ubuntu-24.04` and `windows-2025` runners. Standard hosted
compute in a public repository is free under [GitHub's billing
rules](https://docs.github.com/en/billing/concepts/product-billing/github-actions).
Artifact and cache billing must be checked separately before expanding usage;
this workflow does not alter account billing or the repository's cache limit.
New native build artifacts have a 14-day retention period. Download and verify
needed raw evidence before expiration. Local GPU performance, user hands-on
checks and physical-controller acceptance remain local requirements.
