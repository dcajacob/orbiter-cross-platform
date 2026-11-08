# Current Windows local regression runner

The authorized hosted campaign is `.github/workflows/phase6-qualification.yml`
on `codex/github-qualification`. It reuses the complete existing current Windows
client/cockpit/control, original Windows all38 writer/reload, and four-profile
native/paired-Windows checks with their original simulation commands and budgets.
Hosted provisioning explicitly uses `prepare_hosted_data.py`; the historical
`prepare_data.py` retains the exact bytes pinned by the Lua and UI reference
provenance. The Windows jobs use the Windows 2025 CRT family already qualified
by the accepted Lua/AAP reference;
the compiler is selected from the installed image and recorded, rather than
requiring Visual Studio 2022 on the current Visual Studio 2026 runner image.
Windows 2022 automatic Debug/Release captures remain rejected by the independent
state audit. A successful transport or capture job does not waive that audit. The
portable core matrix also runs on pushes to this branch. Hosted build/result
identities and raw Actions artifacts remain distinct from historical local VM
evidence. The final current-source stock matrix and independent cross-cohort
audits remain explicit pending gates; a successful campaign summary does not
close them. Performance, physical input and controller acceptance stay local.

`phase6-current-windows-sdk.yml` prepares the final current-source SDKs on the
dedicated `qualification/current-windows-sdk` branch. It reuses every existing
Windows application/client/cockpit/control check and forces the complete source
build even if the same-revision cache exists. The same CTest invocation now
retains XML; retention checks every registered process against that XML.
`retain_hosted_sdk.py` verifies every tracked source against the actual producer,
keeps the original packaged application/SDK members intact, and adds the exact
separately linked OpenGL client exercised by the tests. The client suite rebuilds
its test-only behavior driver after SDK verification; those tested variants are
retained separately while the SDK's original driver bytes remain unchanged.
Every production application, module and SDK byte must still match the package.
The archive binds its actual runner/run/source, compiler metadata, unit receipts
and complete member hashes. These artifacts prepare complete stock captures;
they grant no stock, cross-cohort or hands-on acceptance. No local VM setup is
used by this workflow, and the historical worker/provider contracts stay strict.
The actual standard Windows 2025 image reports `win25-vs2026`; retention accepts
that explicitly observed image and `win25`, while preserving the exact value.
A separate failure-only upload retains the original SDK archive, actual CTest
XML and registration files, build metadata and renderer if sealing fails. The
first `b4c883b1` retention attempt failed before this fallback existed; its
application tests and failure receipt remain preserved, but its full SDK was
not uploaded and must be rebuilt. The dedicated retry branch leaves any active
original job running.

The hosted caller explicitly supplies `stock-data-container-v2.lock.json` after
the upstream rolling release removed the original archive asset. This records
the replacement official container separately. `prepare_hosted_data.py` requires
the original profile hash and all 463 original file hashes and lengths; either
the retained original archive or the explicitly declared replacement may supply
those identical inputs. The original stock-data lock, fonts, kernels and
reference inputs are unchanged. Actual container/profile identities are printed
to each provisioning log. No release executable or DLL is staged from it.

`build.py --request PATH` consolidates the historical machine-specific build
scripts. Its versioned request declares the local toolchain, seed repository,
bundle, offline dependencies and fresh build/export roots. It builds both
configurations in a new source checkout, records the actual registered CTest
inventory and results, and preserves existing source/package owners. Build and
unit-test success does not establish simulator runtime acceptance.

These are the exact source-bound runner bytes used for the fresh local Windows
Debug/Release application/SDK/client qualification at `f3e86add`. Configuration
comes from a separately hashed request. The worker invokes the existing ordinary
client, Windows surface/GDI, cockpit and window-control gates and their unchanged
Debug/Release comparators. It records actual child PIDs and exit codes and checks
all source and runtime inputs before and after execution. Raw evidence stays
local.

The system launcher uses the existing logged-in user's token. Its bootstrap
creates a new desktop, launches the worker there, waits for its real exit code
and closes the desktop. It never switches the visible desktop. Retain the exact
request, scripts, actual guest-agent job/terminal receipt, VM identity, system
launch, bootstrap-started/result, worker status, build closure and observations.
A launcher success alone is not a runtime pass.

For new runs, `Closeout/prepare_interactive.py` also prepares an ordinary-session
launch. Start its generated `run.cmd` inside the Windows VM as the signed-in,
non-elevated user. The worker inherits `WinSta0/Default` through normal Python
`subprocess` execution; the package excludes the token launcher and private
desktop helpers. `windows_session_v1.py` only observes the inherited context and
child creation time. A per-session exclusive lock serializes these visible
jobs. Keep the VM desktop idle and do not overlap another qualification campaign.
The launcher reads the Windows machine UUID through CIM and matches the declared
local VM. A console interruption leaves the session lock for explicit inspection
of any surviving simulator processes; it does not automatically retry a campaign.

Preparation requires a committed runner revision and a fresh package path on
the declared host share. Pass `--template EXISTING_REQUEST --output LOCAL_PACKAGE
--guest-root Z:/NEW_PACKAGE --python C:/PATH/python.exe --vm VM_JSON
--runner-commit COMMIT`. The application, SDK, data, paired save inputs, complete
or diagnostic scope, and capacity reserve are conserved from the template.
Original stock scenes run serially, with all original phases and repetitions.
The four worker bodies retain every simulation assertion and comparator; only
their context-helper import and its identity check change.

Retain `interactive-started.json`, `interactive-result.json`, the actual worker
log/result, request, script manifest and VM identity. The independent launch
reader verifies nonce, source hashes, inherited desktop, actual child PID/start,
exit, output hashes and preflight. Existing stock/API auditors select that
versioned receipt path explicitly; historical private-desktop evidence still
requires its original complete chain. Passing launch controls does not qualify
a Windows simulator run. Actual Windows execution and all existing independent
simulation audits remain required.

The worker expects the corresponding complete local build record, source-bound
current runtimes, both instrument/control driver snapshots, locked data and
Mesa files, and the immutable original instrument/control references. Outputs
must be fresh. Its terminal archive is re-read against every member hash;
application/SDK/compiler evidence is preserved separately. Current source and
runtime qualification must use their actual recorded commit; these scripts do
not turn a prior application into a new one.

This covers existing client/GDI/cockpit/control gates. Remaining stock missions,
paused attached-vessel lifetime, current Windows/native complete persistence,
class admission, hardware and Phase 6 acceptance remain separate requirements.

`stock.py` is the separate current-SDK adapter for complete stock writers and
paired exact Windows-save reloads. The existing stock observer is compiled
against the actual current Debug/Release SDK; its only source variant is the
existing 60-to-960 finalized-tick assertion. The v3 local worker declares the
application, SDK, observer and runner independently. Selected and complete
inventories have separate capacity requirements and retain their true scope.
The preserved original-SDK readers remain strict and unchanged.

`audit_stock.py` re-reads real launch/process receipts, raw complete-vessel
traces, begin/end clocks, full frames, cameras and complete saved content. It
requires current Windows and native reloads to consume the same hashed original
Windows save, uses the existing comparison budgets and independently re-audits
retained native captures. It does not reconstruct missing historical receipts
or promote a focused matrix into full38 or class admission acceptance.

The versioned ordinary Actions stock provider lives in `Hosted/`. Its worker
requires the exact retained v3 worker hash and conserves the entire per-lane
simulation, export, repeat and comparison body. Four hosted profile jobs select
one unchanged math lane each; historical two-lane selection remains strict.
The new provider requires all 38 scenes, both repetitions, 960 finalized ticks,
one scene worker, independent runtime/SDK/observer/collector identities, an
8 GiB reserve and an independently audited complete original writer cohort.
It observes the actual inherited session/station/desktop and never creates or
switches a desktop. VM identity and private-desktop claims are rejected.
`phase6-hosted-stock-provider.yml` runs helper controls and a separate read-only
context observation on standard Windows 2025. Neither step executes a simulator
or qualifies stock. Actual API-bound SDK/reference restoration, full captures
and independent cross-cohort audits remain required before acceptance.

The hosted stock v2 route partitions each configuration/math profile by stock
writer and exact-save reload phase to fit standard Actions job limits. Each
cell still executes all 38 scenes twice with 960 finalized ticks; the unchanged
per-phase simulation/export/repeat/comparison body is checked against the
retained worker. A complete matrix requires all eight distinct cells and 608
actual processes from one current application source. Partial phase artifacts
retain a phase-only status and cannot claim a complete matrix.

`phase6-current-stock-preparation.yml` restores the already-tested `c08f9315`
SDKs through their exact successful API run/jobs/artifact digests. It separately
checks every runtime member, the immutable owning source tree and all 28 passed
unit process receipts, then invokes the original passive observer preparer in
its inherited MSVC environment. The original 60-to-960 observation assertion is
the only observer-source variant. The preparation retains actual compiler
receipts and SDK/observer identities; no simulator is executed. Large SDK ZIPs
stay on GitHub. This preparation does not bypass the complete original Windows
writer audit or qualify any current/native stock comparison.
