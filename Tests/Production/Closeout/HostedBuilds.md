# Hosted closeout builds

`phase6-hosted-closeout.yml` runs on the dedicated
`qualification/hosted-closeout` branch. It checks every discovered closeout
control, reuses the complete existing Windows application/client workflow, and
builds the full native stock packages in Debug/Release and automatic/SSE2.
The existing qualification campaign can continue its native runtime and original
Windows captures while this distinct build scope runs. This branch does not
trigger a duplicate portable or full qualification campaign.

The native package job invokes the existing `RemainingVessels/build_native.py`
with `--sanitizers --include-unit-tests` and the unchanged dependency pins.
It builds the normal host, all stock families, both retained diagnostic hosts,
registered engine units, and unchanged upstream C++/Lua unit bodies. It executes
the complete registered test inventories, discovers actual upstream Catch cases,
and retains source-bound binaries, generated sources and real test results.
Loading ASan before the Python math probe permits instrumented shared-library
loading without disabling address, leak or undefined-behavior diagnostics.

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
