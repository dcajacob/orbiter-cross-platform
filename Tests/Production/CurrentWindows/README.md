# Current Windows local regression runner

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
