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
Frozen numerical, image and scenario references are unchanged. Fresh matching
packages and the no-observer paused-world/F5 lifetime regression are required
before runtime acceptance. The production class gate remains closed.
