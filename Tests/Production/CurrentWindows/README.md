# Current Windows local regression runner

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
