# Paused attached-vessel teardown

Closing the unchanged three-vessel `Atlantis ISS Resupply` scene while paused
exposes a use-after-free in `Vessel::UpdateAttachments`. Both initial native
Release/SSE2 attempts terminate under ASan. Their original logs remain local.

The scene lists Leonardo after its docked shuttle parent, so world cleanup
deletes Leonardo first. Before the first passive update, Leonardo has no proxy
body. `DetachFromParent` consequently returns false during attachment cleanup,
leaving the shuttle's attachment pointing to the deleted payload. Deleting the
shuttle then undocks it and updates its attachments through that stale pointer.
Running the scene first initializes the proxy body, which explains why a normal
flight capture can miss the paused shutdown failure.

The cleanup candidate retains normal release and its existing physical updates.
If release cannot run during definition destruction, it removes the reciprocal
attachment links before deleting their storage. It handles both parent-first
and child-first cleanup. The public release operation, flight calculations,
scenario, module capabilities and admission policy remain unchanged.

The source-conservation audit accepts exactly this cleanup branch and restores
the complete original method before comparing the remaining implementation.
Frozen numerical, image and scenario references are unchanged.

A fresh matching Release/SSE2 ASan/UBSan package from `e411b1c4` now passes the
[permanent no-observer regression](../../Tests/Production/RemainingVessels/paused_attachments.py).
Twenty complete paused worlds, nineteen real F5 reloads and normal Escape exit
produce twenty clean graphics-context deletions and 1,234 successful presents.
All sixty finalized vessel rows remain finite at tick/time zero, with ISS docking
and both reciprocal Leonardo attachment links intact. ASan, UBSan and unsuppressed
LSan report no findings. The original three-vessel scenario bytes seed F5; this
does not claim actual-save persistence or flight parity.

The initial build-tool attempt failed because LSan cannot inspect processes under
the execution sandbox's tracing. Its failed record and log remain local. The
unchanged recorded build commands were resumed outside tracing, with source,
archive and generated-input guards checked before and after compilation. This
was an environment failure in the mesh compiler, not a simulator test pass.

[The original verification record](AttachmentTeardownVerification.json) pins the
local baseline failure, package and completed capture and remains unchanged.

Four fresh ASan/UBSan packages from `f82b7392` now complete the same regression:

| Native profile | Paused worlds | Real F5 reloads | Successful presents |
| --- | ---: | ---: | ---: |
| Debug automatic | 20 | 19 | 1,245 |
| Debug SSE2 | 20 | 19 | 1,237 |
| Release automatic | 20 | 19 | 1,231 |
| Release SSE2 | 20 | 19 | 1,229 |

All four processes exit normally: 80 graphics contexts delete cleanly, 240
finalized vessel rows remain finite at tick/time zero, and the original docking
and reciprocal payload links survive every replacement. All four packages share
the same 622 production input hashes. Each capture protects 901 source, runtime,
generated and fixture inputs plus all 1,130 staged resources. No preload
observer or sanitizer suppression is used.

The independent audit re-reads the actual compositor key acknowledgements,
state rows, full-sized framebuffers, lifecycle records, sanitizer logs and every
guarded input. The [four-profile verification record](AttachmentTeardownProfilesVerification.json)
pins the completed audit and captures. Exact copies of all 798 consumed source
and fixture files are preserved locally and checked against all four captures;
runtime and generated compiler inputs remain in their guarded packages.

The first combined audit stopped because the historical Release/SSE2 capture's
guarded test README had changed after capture. Its ten pinned raw-evidence files
and every other guarded input still match. That failed audit remains retained;
the fresh Release/SSE2 build and capture replace it in the new matrix without
waiving a guard.

The [current Windows normal-cleanup regression](WindowsAttachmentLifetime.md)
now also passes eighty worlds in all four profiles at `bdfd067f`, with its full
new launch chain independently audited. Full numerical/image and mission
qualification remains outstanding. Original scene bytes still seed F5, so these results establish
paused lifetime coverage. The production class gate remains closed and Phase 6
remains incomplete. Raw runtime evidence stays local; no hosted build was used.
