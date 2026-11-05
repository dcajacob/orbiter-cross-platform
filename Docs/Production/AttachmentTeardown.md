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

[The verification record](AttachmentTeardownVerification.json) pins the local
baseline failure, fresh package and completed capture. Other native profiles,
Windows regression and full numerical/image qualification remain outstanding.
The production class gate remains closed and Phase 6 remains incomplete. Raw
runtime evidence stays local; no hosted build was used for this result.
