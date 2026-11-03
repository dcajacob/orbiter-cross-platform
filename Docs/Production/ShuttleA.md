# Shuttle-A native integration candidate

Phase 6 now compiles the original Shuttle-A production module and its payload
in the native cockpit build. Its comparison candidate now admits only the
initial capabilities observed in all four audited Windows profiles. Required
modules still use the checked loader. Native state/image comparisons remain
pending; this does not increase the accepted stock-corpus pass count or complete
Phase 6.

The port retains the original flight and parachute calculations, resources,
animations, panel/VC instruments, attachment logic and Lua methods. The source
audit compares all 40 original implementation/header files against preserved
revision `f725194209634f7fd5d1d44d426cfa9b5e303e37`. Windows keeps its SDK
types/layouts and scenario-editor page. Native loading uses the existing checked
module ABI, with one shared drawing-resource lifetime across simultaneous ships.
The native SDK build identity includes the module sources, common instruments
and source mesh used to generate group IDs.

Native SDK adapters delegate rectangular colour fills, mesh-group insertion,
surface/texture loading and legacy panel redraw requests to the existing
production renderer and Pane implementations. Native VC bitmap resources load
the original BMP bytes from staged files. Packed RGB constants have the same
values as the original Windows macro. The Lua declaration linkage is made
consistent with its existing static definitions; method bodies are unchanged.

The new Windows observation matrix covers all six unchanged Shuttle-A scenes
and four complete DG scenes containing Shuttle-A. It preserves every declared
ship, repeats each session, records all vessel states/capabilities and docking
ports, and keeps the existing numerical and image budgets. It builds only an
observer against the preserved application, SDK and graphics client. The four
original Debug/Release automatic/SSE2 profiles must be captured and audited
before admitting native capabilities.

See [the fixture and commands](../../Tests/Production/ShuttleA/README.md).
Native state/image comparison, interactive Shuttle-A controls, payload
deployment and Shuttle-A flight/cockpit lifetime checks remain pending. The Windows-specific
Shuttle-A scenario-editor page also needs a native UI implementation.

Local integration checks now pass for the compiled candidate `778b6c58`:
14 existing station sessions match the original Windows state/image captures,
with 840 presentations and unchanged budgets. The updated observer also
re-audits all 56 original station sessions successfully. This protects the
existing integration scope while Shuttle-A qualification is pending.

Sanitizers then exposed a startup leak in four payload scenes: each retains
six parent-name strings, totalling 36 bytes, when rejection occurs before
post-creation. Cleanup revision `2d9367c5` adds two destructor lines to release
those pending names. The normal attachment initialization still consumes and
clears them as before. No calculation, callback order or header layout changes.
Source controls reject removal of the cleanup and an incorrect scalar delete.

Fresh Release and sanitizer builds pass. All ten unchanged candidate scenes
now reach the closed capability gate, exit with code 1 and delete their graphics
contexts with zero sanitizer findings. They remain failed stock scenarios.
The cleanup revision also passes eight original Windows flight comparisons
in the established ShuttlePB docking, approach, attachment and lifetime fixtures,
plus twenty sessions and
1,200 presentations with clean sanitizer exits and identical states. Actual
Fontconfig and GDK candidate mappings are retained for all nine processes.
The pinned Mesa candidate was requested in the invocation; the early mapping
snapshots do not prove the later driver mappings.

The [machine-readable checkpoint](ShuttleAStartupVerification.json) records
these scopes and their hashes. The verified local evidence archive is
`out/phase6-shuttle-a-initial-evidence-v1.tar.gz`: 121,654,119 bytes,
3,206 members, SHA-256
`98ea203c928212754b908d59d39aa282a1ae6b54505dc8c24cd21b68c67002a0`.
It retains both runtimes, the four leak cases, clean targeted captures, original
comparisons, source controls and replay recipes. Remote preservation remains
open. All four original Windows Shuttle-A profiles are now downloaded, hash-verified
and audited: 80 sessions, 4,800 presentations and 38,552 finalized all-vessel samples.
Their complete traces, deterministic repeats and Debug/Release pairs pass the
unchanged budgets. Native Shuttle-A state/image qualification is still pending.
The subsequent complete instrumented sweep on cleanup revision `2d9367c5`
is audited: all 157 scenarios were attempted, with 44 passed, 113 failed, no
signal-terminated processes and no sanitizer findings. Its inventory finds
119 complete dependency sets; the capability gate was still closed for that
capture. Every failure and the seven frozen inventory metadata discrepancies
remain recorded. This is an audited incomplete corpus, not full stock acceptance.

The new admission candidate checks SDK version, mesh/thruster/propellant counts,
docking and attachment counts, focus eligibility, transponder, size, inertia
and cross sections against the observed original classes. Shuttle-A payload
mass remains the original scenario-controlled quantity. Only the observed
initial one-mesh cargo configuration is admitted; restored deployed-parachute
configurations still need their own original observations. None of the flight,
parachute or attachment calculations are changed by this policy.
