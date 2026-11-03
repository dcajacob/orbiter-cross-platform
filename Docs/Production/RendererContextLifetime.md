# Renderer state and windowing ownership

The complete 157-scene instrumented sweep now returns to **44 passes and 113
failures**, with zero signal terminations and zero ASan/UBSan/LSan findings.
Every unchanged scenario and declared ship is retained. The remaining failures
are 112 unavailable-dependency cases and the preserved GeneralApiTest assertion.
This is an audited incomplete corpus, not full stock acceptance.

The preceding fully instrumented runtime passed 25 scenes and failed 132. Five
scenes stopped on an invalid `normalizeNormals` boolean; fourteen reported a
one-byte allocation at exit. Actual process mappings resolve the allocation
to `OGLMesh::CopyGroup`, reached through base-structure meshes. Its empty vertex
array is allocated with `new[0]`, and the vertex-count guard prevented release.

Two renderer sites change. The constructor value-initializes its render context
before legacy planet paths save and restore cached state. Mesh-group cleanup
releases its owned vertex array regardless of count. Headers, member layouts,
geometry calculations and processing order are conserved. Source controls
compare every other byte with `f1edc28a` and reject removed cleanup or unrelated
vertex-count changes. The complete 444-file conservation audit also passes.

Fresh Release and Debug instrumented renderer builds use exact copies of the
unchanged engine, modules and matching SDK header. All fourteen Release station
captures pass the audited original Windows state, capability, port, camera and
full-frame image budgets. Sixteen targeted instrumented stock regressions pass,
followed by the complete 157-scene sweep above. No accepted reference, asset,
scenario, numerical threshold or pixel budget is refreshed.

## Repeated GDK initialization

The previous twenty-session test completes every presentation and context
deletion, then reports 152 bytes in 19 allocations from the installed GDK
backend setter. The exact Ubuntu GTK 3.24.52 source duplicates the supplied
backend string and overwrites the previous pointer. The private candidate owns
setter copies separately from the borrowed default `"*"`, duplicates a new input
before releasing the old copy, and preserves backend selection and GTK
decorations. Public headers and all 761 GDK symbol names/types are unchanged.

Installed and rebuilt-baseline public-API controls reproduce the same 152 bytes
and 19 allocations. The candidate becomes clean, including the borrowed-default
path, while still reporting an independent deliberately lost 73-byte allocation.
The [pinned builder and controls](../../Tests/Production/GdkLifetime/README.md)
reproduce the result in fresh prefixes. Compiled runtime paths remain `/usr`,
`/etc` and `/var`; the builder copies only libraries and notices and never runs
system installation rules.

The final candidate passes eight instrumented Windows flight comparisons and
twenty actual application sessions: 1,200 presentations, identical repeated
states, all visuals released, all contexts deleted and clean sanitizer exit.
Actual mappings verify the candidate in all nine application processes.
It also passes sixteen real Wayland input flows on Intel and llvmpipe: both
gliders, panel/VC and 1x/2x, totaling **13,190 presentations**. Keyboard, focus,
RCS picking, camera input and held-button shutdown retain their original gates.
The independent focus client and compositor use their normal runtimes.

Engine and renderer C/C++ sources and the private Fontconfig/GDK candidates are
instrumented. Prebuilt CSPICE and other system libraries retain their builds.
Leak detection and undefined-behavior checks stay enabled without suppressions,
root annotations, cache resets or decoration-policy changes. System installations
are unchanged. The first private-prefix GDK prototype and the final build with
system runtime paths have separate binary identities and retained evidence.

[RendererContextLifetimeVerification.json](RendererContextLifetimeVerification.json)
records identities, results and local artifact hashes. Phase 6 remains in
progress: required stock modules, the GeneralApiTest assertion, current hosted
qualification, final hardware performance and durable remote evidence still
need work. The user reports no physical controller is available; that hardware
gate remains unverified.
