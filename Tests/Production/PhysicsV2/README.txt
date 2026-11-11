Shared physics version: assembly-contact-v2

Approved changes are exactly the three-hunk correction.patch in the shared
SuperVessel.cpp used by both Windows and native Linux:
- Recompute actual planet/proxy and surface state after assembly defaults.
- Retain detected ground contact for the original integration retry.
- Forward the original ground-contact retry policy to each component.

The original source guards, old extraction ledger, tests, references, failed
captures and tolerances are unchanged. source.py first checks the complete exact
approved delta and original guard hashes. It then creates an isolated sparse
checkout of original source 07044f8e and runs the unchanged original guards there.
The original guard still rejects v2 when invoked directly, as it should.

Qualification entry point:
.github/workflows/phase6-physics-v2-qualification.yml
Standard ubuntu-24.04 and windows-2025 runners only; no local heavy build.

Native builds opt in with --physics-version assembly-contact-v2. Original build
invocations retain their existing source contract. Fresh build records name the
physics version, source proof and actual generated SDK header. The Windows
reusable workflow opts in explicitly and retains every original client test.

Original controls are replayed on their exact baseline. New version controls
check the actual corrected source separately. All original engine/upstream test
bodies and case identities run again on the freshly compiled application.
Passing source controls or a package build does not grant qualification.
