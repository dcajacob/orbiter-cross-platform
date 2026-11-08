# Orbit label storage and Windows DLL staging

The Orbit MFD used a sixteen-byte local label buffer. Its unchanged distance
formatter writes fixed-point astronomical-unit values, which can exceed that
space even for finite inputs. The formatter's shared 256-byte buffer also
overflows for distances near the largest finite double. Both arrays now hold
512 bytes. The text, numerical operations and public layouts are unchanged.
The conservation audit permits exactly these storage changes.

The focused sanitizer regression compiles the actual DisplayElements, DistStr
and FloatStr bodies. Forty ordinary label sets remain byte-identical to the
original implementation. Twenty-four large-value sets and both signs of the
largest finite double complete without sanitizer findings or truncation.
Restoring either original buffer reproduces its sanitizer failure. These are
formatting tests with read-only inputs, not flight or propagation acceptance.

A separate Windows build regression exposed an old test-side boundary DLL
after an incremental SDK-token change. The import library remained unchanged,
so the executable did not relink and its post-build copy did not run. Windows
consumers now explicitly depend on the actual boundary DLL when linking.

An actual MSVC/Ninja control in the local Windows VM reproduces the stale DLL
with the original helper and loads the updated DLL with the corrected helper.
Both retain identical import-library bytes across the change. Its nonce-bound
child exit and all 75 archived members were independently checked on the host.
This verifies build staging; matching full application runtime gates remain
required.

[Evidence bindings](OrbitLabelStorageVerification.json) record the focused
results. The merged candidate requires fresh matching Windows/native builds,
normal-host corpus and save/reload checks, named missions and desktop acceptance.
The central closeout ledger remains incomplete. Historical evidence paths in
removed worktrees require recovery or fresh observation before closeout.
