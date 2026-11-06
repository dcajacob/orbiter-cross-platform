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
The same worker also accepts explicit diagnostic selections containing scene003
for its existing mutation controls. Selected status, arguments, case/repetition
counts and process receipts are checked separately; even an explicit selection
of all 38 scenes remains diagnostic. Its storage reserve scales with work size.
The selected worker path currently has fixture coverage; actual audited Windows
diagnostics used the separate passive-observer collector.
The historical v1 transport and its `O:` receipt reader remain unchanged.
The v2 path also has independently audited actual diagnostic launches: normal
user workers, private desktop creation/closure, actual simulator PIDs and clean
exits, runtime roles, declared share/capacity preflights and retained raw hashes.
Those scene003 diagnostics do not qualify a fresh full38 campaign or fill
missing historical launch receipts.

`storage.py` restores every archive member to a temporary directory and hashes
it through a separate file read. `reclaim_duplicates_v1.py` refuses removal
until *all* requested VM duplicates match those restored hashes. It removes
only named generated trace/frame files from closed Full38 output directories;
source, scenarios, modules, dependencies, data and reference packages remain.
The local VM resumed. All four original archives restored and independently
verified (21,480 members, 8,038,366,358 decoded bytes). The closed cleanup removed
7,904 matching generated duplicates, reclaiming 7,611,832,829 bytes. The removal
set was independently checked against the request. Full campaigns still require
the separate 8 GiB free-space preflight; the explicit diagnostic reserve is 1 GiB.

Run the local controls before qualification:

```sh
python3 -B Tests/Production/Closeout/Runner.Test.py
python3 -B Tests/Production/Closeout/Transport.Test.py
python3 -B Tests/Production/Closeout/Storage.Test.py
python3 -B Tests/Production/Closeout/Manifest.Test.py
python3 -B Tests/Production/Closeout/run_controls.py --output NEW_JSON
```

The discovered controls include disposable real
process trees; `run_controls.py --output NEW_JSON` records actual totals and
source hashes. Fixture captures do not count as simulator acceptance. Eight
real retained scene003 writers have also passed the reuse-only coordinator and
fresh independent Windows comparisons. Those writer passes do not qualify reloads.
The repaired `81dcc014` native matrix now also has sixteen complete, independently
audited scene003 writer/reload runs in four profiles and two repetitions. Those
selected captures qualify only that focused native comparison; full campaigns,
current-Windows coverage and normal admission remain open.
