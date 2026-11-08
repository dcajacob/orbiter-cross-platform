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
