# Phase 6 closeout tools

`Docs/Production/Phase6Closeout.json` is the single finite ledger. Its fourteen
gates retain the approved acceptance requirements and explicit failures. The
manifest validator checks checklist and hash bindings; it is not a substitute
for independently reading simulation evidence. No gate is currently closed by
this implementation. Physical-controller acceptance remains blocked.

`run_native.py` replaces the local ad hoc persistence coordinators. Its JSON
request names the owning checkout, immutable collector and runtime commits,
four package paths, declared data/providers/Windows references, and either
`selected_cases: null` for all 38 scenes or an ordered explicit diagnostic list.
Two collectors with at most two jobs each enforce the four-simulator limit.
The existing capture, state/camera/frame/save comparators and independent native
reader retain their complete checks. No physics formula, ordering or budget changes.

A `reuse` entry names a closed capture, its SHA256 and its actual original
`collector_commit`. Reuse re-runs the owning independent reader and comparisons;
it never relabels an old capture with the current reader's commit.
`--verify-reuse-only` audits those declared stages and launches no collectors.
It earns only `audited-reusable-captures-only`, not a completed campaign.
Cancellation records collector exit receipts and checks PID start tokens before
signalling observed descendants, including separate-session compositor children.
Completed stages remain independently auditable when another stage fails.

The v2 Windows worker and descriptor live under `LocalVM/`. They use explicitly
declared roots and a hashed host-share witness, validate real capacity before
running, and record separate application, SDK, observer and runner identities.
The worker currently supports original-Windows reference captures; current
Windows needs its matching runtime adapter and is explicitly rejected by this
worker. `receipts.py` reads the generic local launcher/private-desktop chain
and complete process coverage separately from numerical/runtime auditors.
The historical v1 transport and its `O:` receipt reader remain unchanged.
The v2 Windows path has fixture coverage; a fresh actual VM run remains open.

`storage.py` restores every archive member to a temporary directory and hashes
it through a separate file read. `reclaim_duplicates_v1.py` refuses removal
until *all* requested VM duplicates match those restored hashes. It removes
only named generated trace/frame files from closed Full38 output directories;
source, scenarios, modules, dependencies, data and reference packages remain.
The staged cleanup has not run: the VM became paused with reason `user`.

Run the local controls before qualification:

```sh
python3 -B Tests/Production/Closeout/Runner.Test.py
python3 -B Tests/Production/Closeout/Transport.Test.py
python3 -B Tests/Production/Closeout/Storage.Test.py
python3 -B Tests/Production/Closeout/Manifest.Test.py
```

The discovered controls include disposable real
process trees; `run_controls.py --output NEW_JSON` records actual totals and
source hashes. Fixture captures do not count as simulator acceptance. Eight
real retained scene003 writers have also passed the reuse-only coordinator and
fresh independent Windows comparisons. Reload qualification remains failed.
