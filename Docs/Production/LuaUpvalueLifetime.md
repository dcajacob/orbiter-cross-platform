# Defined native Lua upvalue-list guards

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
Lua calculations remain unchanged. Under the same unsuppressed sanitizers,
the prototype passes closure creation, shared captured variables, 5,000 retained
closures, closing and repeated garbage collection. Its stress output is
byte-identical to the unchanged normal interpreter.

The native build now adopts those two guards in a generated copy of `lfunc.c`.
`Tests/Production/NativeLua/upvalue-source.lock.json` pins all 55 original C and
header inputs and the effective file hash. The generator verifies every input,
rejects additions, symlinks and drift, checks the result and leaves the downloaded
tree untouched. Both the native library and command-line interpreter compile
the checked copy. The Windows dependency and original headers are unchanged.
The adaptation and its lock also enter the native SDK build identity, so the
full engine and its modules are rebuilt together.

The standalone native build passes all four tests with C and C++ instrumented
by unsuppressed ASan/UBSan/LSan: upvalue lifetime, source-integrity controls,
interpreter handoff and stock script paths. The integrity test also rejects
edits to the generated file and verifies idempotent generation. A fresh Release
engine passes all five preserved Windows Lua/AAP schedules: event timing,
controls, air data and cockpit state are byte-identical on the matching default
math profile. The accepted reference ZIPs were verified again offline; their
bytes and all comparison budgets are unchanged.

The Lua-only fully instrumented engine and renderer get past the Lua failure, but
stop before Wayland interaction at `Scene.cpp:544`: the renderer downcasts a
`vStar` to `vPlanet` while building its combined star/planet render list.
This retained failure prevents a full Wayland sanitizer qualification. No
sanitizer is disabled, error ignored or reference/budget refreshed. Subsequent
[renderer and planet initialization repairs](RendererDefinedBehavior.md) get
through actual input and context teardown; process-level dependency leaks still
prevent full Wayland sanitizer qualification.

Local evidence is retained in `out/phase6-lua-upvalue-repro/`, including both
failed original/first-prototype runs and `prototype-verification.json` for the
two-guard candidate. The full startup failure and exact pre-station-policy
runtime identities are in `out/phase6-wayland-asan-system-dg-panel-1/` and
`out/phase6-wayland-asan-build-snapshot.json`. Integrated evidence is recorded in
[LuaUpvalueVerification.json](LuaUpvalueVerification.json), with local captures
in `out/phase6-lua-defined-asan/`, `out/phase6-lua-guards-regressions/` and
`out/phase6-lua-guards-asan-system-panel-1/`. Fresh normal and instrumented
runtime directories are retained separately from earlier accepted builds.
