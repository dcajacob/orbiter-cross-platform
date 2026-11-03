# Fully instrumented Lua upvalue-list failure

The fresh Wayland sanitizer build instruments C as well as C++, with
`-fsanitize=address,undefined -fno-omit-frame-pointer`. With unsuppressed
ASan/UBSan/LSan, DG initialization stops in the pinned Lua dependency before
Wayland interaction begins. This run does not qualify Wayland sanitizer input
or teardown.

`luaF_findupval` at `lfunc.c:58` converts an empty `GCObject` list to its union
member before testing whether the resulting pointer is null. UBSan reports
member access through a null pointer. A minimal Lua closure reproduces the same
failure without the simulator or graphics client. An isolated prototype that
guards this first conversion then exposes the equivalent empty-list conversion
in `luaF_close` at line 99.

A second isolated prototype checks each list pointer before its conversion.
The nonempty-list loop bodies, pointer updates, allocations, GC operations and
Lua calculations remain unchanged. The original downloaded sources and the
production dependency are untouched. Under the same unsuppressed sanitizers,
the prototype passes closure creation, shared captured variables, 5,000 retained
closures, closing and repeated garbage collection. Its stress output is
byte-identical to the unchanged normal interpreter.

This is a tested prototype, not a production fix. Adoption still requires a
hash-checked native build adaptation, source provenance, fresh matching modules,
original Lua/AAP comparisons and repeated complete Wayland sanitizer flows.
No sanitizer is disabled, error ignored or reference/budget refreshed.

Local evidence is retained in `out/phase6-lua-upvalue-repro/`, including both
failed original/first-prototype runs and `prototype-verification.json` for the
two-guard candidate. The full startup failure and exact pre-station-policy
runtime identities are in `out/phase6-wayland-asan-system-dg-panel-1/` and
`out/phase6-wayland-asan-build-snapshot.json`.
