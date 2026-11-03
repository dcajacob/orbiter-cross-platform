# Native Lua process exit and resource lifetime

The unchanged `Tests/VesselApiTest.scn` passes all of its Lua assertions and
then calls `oapi.exit(0)`. The original native implementation called `exit`
directly, bypassing application destruction, graphics context deletion and
renderer cleanup. The retained pre-fix instrumented runtime reproduces the
15,264-byte leak in 76 EGL allocations and exits with LeakSanitizer status 1.
That failed result remains separate from the repaired runs.

Commit `b1e3f1d60485149f5df63b5e89b531cb8ed0d8cf` changes only native exit
handling. Windows retains its original `exit(code)` body. The native function
records the requested integer exit code and cancels Lua execution through Lua's
own protected calls. An exit-only helper uses the pinned Lua runtime's thread
list to cancel protected calls and nested coroutines; it also bypasses Lua
error handlers. The exit repair adds no edits to the pinned Lua sources. Ordinary execution
does not install these cancellation hooks.

The outermost interpreter call raises the native exit request only after
`lua_pcall` has returned. A nested native callback transfers cancellation back
to its caller before Lua can resume. The existing worker exception handoff
returns control to the simulator thread. Application destruction then uses
the existing shutdown order before `main` returns the requested exit code.
The exception's type and destructor live in the engine library, which stays
loaded while the interpreter modules unload. No Windows SDK layout changes
were made; simulation formulas are unchanged.

The [runtime verification](LuaProcessExitVerification.json) contains 17 process
results: one retained failing baseline and 16 repaired runs. The repaired
Release automatic and instrumented Debug automatic builds each ran eight
cases: asynchronous exit codes 0 and 7, synchronous exit, direct simulator-thread
exit, `xpcall`, nested coroutines, a nested native callback into another Lua VM,
and the unchanged full vessel API scenario. The fixtures retain every vessel
in their complete stock scenes.

All 16 repaired processes return the requested code, delete their graphics
contexts, and leave an existing save file byte-identical. The injected cases
stop at the dispatch boundary after four presentations, with no following Lua
instruction, native step completion or presentation. The unchanged vessel API
scenario passes all assertions, presents 13 frames and exits with code zero.
Together the repaired runs present 82 frames. The instrumented processes have
zero AddressSanitizer, UndefinedBehaviorSanitizer or LeakSanitizer findings,
with leak detection enabled and no suppressions. Actual CMake configurations,
compiler instrumentation, linked sanitizer libraries, private dependency
mappings and retained runtime hashes are checked separately.

Five standalone sanitizer tests also pass, including nine cancellation cases
using the real pinned Lua interpreter, the existing execution handoff,
upvalue lifetime/source integrity and stock script file access. The initial
cancellation test exposed an `xpcall` error-handler continuation; its failed
log is retained. The corrected tests verify that cancellation stops script
instructions and still permits native resource finalization. All 479 owning
source files pass the source-conservation audit, and both fresh application
packages match the committed owning sources exactly.

Six ordinary full-scene regression processes also pass. Both unchanged lunar
transfer scenes produce byte-identical all-vessel physical state files and
byte-identical full frames against the retained pre-exit-fix Release runtime.
Those runs present 360 frames with clean teardown, including instrumented
Debug runs. They qualify ordinary behavior separately from intentional early
process termination.

The verified local evidence bundle is
`out/phase6-lua-process-exit-evidence-v1.tar.gz`: 56,118,791 bytes and 1,404
members, SHA-256
`2939629a1d6b177cc5eef565e436c8ae783032f7a4151082c4262ba9551fdaf5`.
All payload hashes were rechecked after packaging. It includes the two matching
application packages, source snapshots, raw exit and ordinary-scene results,
build logs, standalone test records and the pinned Lua archive. The baseline
runtime is referenced through the preceding verified Transfer MFD bundle.
Asset and font collections are excluded; remote preservation remains open.

The separate [stock exit observation](LuaStockExitVerification.json) now passes
an independent original/native comparison in all four Debug/Release and
automatic/SSE2 profiles. Two complete processes per profile on each platform
produce 104 presentations, 896 all-vessel samples and 1,680 docking-port samples
per side. Every process contains all eight stock vessels, 60 ordered script
log events and 28 assertion-pass records. The original Windows application,
SDK, graphics client and stock script remain unchanged. Native Debug automatic
uses the explicitly recorded AddressSanitizer/UndefinedBehaviorSanitizer build;
the other three native profiles use normal Debug or Release builds.

All seven numerical error maxima are zero in all eight comparisons, with the
existing numerical budgets unchanged. Vessel capabilities, local docking-port
geometry, normalized completed-frame boundaries and actual math implementations
also match. Both platforms intentionally exit after 13 completed presentations
and 14 finalized state snapshots. Native processes additionally delete their
graphics contexts and preserve the existing save. Twelve damaged-capture checks
on each original and native profile reject 96 altered captures; three comparison
identity checks reject forged observer sources and reported or raw math records.

The four exact original ZIPs are preserved in the public
[stock exit reference release](https://github.com/dcajacob/orbiter-cross-platform/releases/tag/phase6-stock-lua-exit-original-v1).
The preservation workflow succeeded, and a fresh download without authentication
rechecked all four archive hashes and independently audited all eight original
processes. The source, archive and metadata pins in
`Tests/Production/NativeLua/StockExit/observations.lock.json` prevent automatic
reference refresh. The initial image-probe setup failure is retained separately
and remains unqualified; this checkpoint makes no new image-comparison claim.

The complete stock-exit parity evidence bundle is
`out/phase6-stock-lua-exit-parity-evidence-v1.tar.gz`: 31,514,023 bytes and 1,120
members, SHA-256
`e5a1c6094b39d30f74feeb8b4cf5eaa752aee64a365d0f138fd5040b73da6d69`.
Every payload hash was checked after packaging. The bundle contains all four
profile captures, the original archives, failed initial attempt, final auditors
and controls, the full owning-source snapshot and both fresh SSE2 packages.
The two automatic packages are retained in the preceding Lua process-exit
bundle. Asset and font collections are excluded. Remote preservation of the
complete native/parity bundle remains open.

The stock-corpus termination rules are unchanged at this checkpoint. The
historical 157-scenario sweep remains
112 passed and 45 failed; the original failed result is not rewritten as a
pass. Hosted checks for the repair, other missing stock modules/dependencies,
final hardware testing and remote evidence preservation remain open. A
physical controller remains unavailable and unverified.
