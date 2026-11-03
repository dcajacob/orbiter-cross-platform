# Complete unchanged stock-corpus readiness

This fixture attempts **all 157** scenarios identified by the frozen production
source lock. Every source file must match its locked LF hash and its staged raw
bytes must remain identical. No ship is removed, replaced or edited to make a
scenario run. The frozen lock and accepted references are never rewritten.

Vessel blocks are parsed anew from those verified bytes. Seven frozen inventory
metadata entries mishandled indented blocks or vessel property lines; the file
hashes remain correct. The new report records those metadata discrepancies
separately. Inventory objects are not runtime acceptance evidence.

Dependency inventory follows the actual `Vessel::OpenConfigFile`,
`Vessel::LoadModule` and `ReadGenericCaps` paths: search Config/Vessels then
Config, resolve declared base configurations, and require the explicitly named
native module. Case/separator normalization and ambiguous-alias rejection match
the resource resolver. A class with no Module entry uses the original
configuration-defined VESSEL implementation. That is how stock ISS, Mir and
Wheel work; it is not permission to replace a missing required module.
File readiness does not prove runtime ABI compatibility or host qualification.

The current host additionally restricts allowed class/capability combinations.
The last independently audited complete sweep, at runtime source `09eeed20`,
attempted all 157 unchanged scenarios: **112 passed and 45 failed**. That
historical result remains unchanged. Transfer MFD and explicit Lua-exit repairs
have since passed targeted complete-scene regressions; a fresh full sweep is
required to establish their effect on the corpus. The earlier results below
remain historical checkpoints.

The earlier complete sweep at runtime source `9418ae29` found 45 scenarios with their
declared configuration/module files present. Mir/Wheel now have an explicitly
qualified local Release automatic capability policy and seven formerly rejected
scenarios pass. GeneralApiTest still fails its preserved original-Windows
Earth-obliquity assertion. The 112 remaining scenarios lack staged class
configurations and their source modules. All failures remain failures: the
result is **44 passed, 113 failed**, improving the preceding `2c00d29b` baseline
of 37/120. This is not full stock acceptance. The same 25 dependency-incomplete
cases terminate by signal in both historical runtimes. The subsequent startup
lifetime fix passes clean-rejection regressions for all 25, without qualifying
their missing dependencies; see [startup lifetime](../../../Docs/Production/VesselStartupLifetime.md).

Each ordinary scene must complete 60 original 0.25-second frames with normal
context deletion and complete finalized ticks 0 through 60. At every tick the
actual original vessel trace must contain the entire declared ship manifest,
including non-focus ships and exact class names. Lua/runtime/sanitizer errors
are retained. Missing modules, exceptions and process failures cannot silently
turn into configuration-only successes. The current host's controlled default
epoch for missing/invalid numeric dates is recorded; this does not qualify
wall-clock Today semantics. This is an initialization/smoke sweep, separate from
interactive acceptance and additional original Windows state/image comparisons.

`Tests/VesselApiTest.scn` has one explicit intentional-exit policy, established
by the independently audited original Windows Debug/Release automatic/SSE2
observations. Its locked scenario and script bytes must match. Before running
the scene, the harness re-audits all four original profiles and verifies the
actual native build inputs, configuration, math implementation and binaries.
A read-only SDK observer retains all eight original vessels and every docking
port at the unchanged session boundaries. Acceptance requires the original
13 presentations and 14 finalized snapshots, all 60 ordered assertion log
events and 28 pass records, exit zero, context deletion and an unchanged
existing save. Every SDK state and local docking-port observation is compared
to its original profile with the existing numerical budgets. Other early
exits retain the ordinary sixty-frame failure. No script or ship is modified.

The run and independent audit record the selected build manifest, all 479
owning sources, actual CMake cache, retained libraries, observer inputs and
explicit sanitizer settings. The observer inputs must match their recorded
immutable producer commit. Instrumented sweeps require leak detection with
no suppressions. All protected files must remain unchanged throughout the run.

```sh
python3 -B Tests/Production/StockScenarios/run.py \
  --backend wayland --executable out/phase6-lua-exit-asan-engine/orbiter-production \
  --assets out/phase6-shuttle-a-resources-v2 --data out/native-celestial-data \
  --modules out/phase6-lua-exit-asan-engine/NativeModules --planets out/archive-data \
  --build-record out/phase6-lua-exit-build-asan/build.json \
  --runtime-source-commit b1e3f1d60485149f5df63b5e89b531cb8ed0d8cf \
  --stock-exit-reference out/phase6-stock-lua-exit-public-replay-v1 \
  --output out/stock-full-smoke

python3 -B Tests/Production/StockScenarios/verify.py \
  --capture out/stock-full-smoke --assets out/phase6-shuttle-a-resources-v2 \
  --modules out/phase6-lua-exit-asan-engine/NativeModules \
  --runtime-source-commit b1e3f1d60485149f5df63b5e89b531cb8ed0d8cf \
  --stock-exit-reference out/phase6-stock-lua-exit-public-replay-v1 \
  --output out/stock-full-audit.json
```

Use an owned correctness-test display, matching backend, and appropriate
runtime library path. All output directories/files must be fresh. The sweep
exits nonzero when any scenario fails and still saves every attempt. The audit
can successfully validate an incomplete sweep, but reports `audited-incomplete`
and retains every failure. It never equates that status with passing the
corpus gate. `--inventory-only` and selected `--case` runs are not complete
smoke qualification.

`Inventory.Test.py` checks indented/shorthand parsing, required-module failure,
intentional configuration-defined vessels, path escape and directory-alias
rejection against temporary fixtures and all locked scenario bytes.
`Manifest.Test.py` removes a non-focus ship at tick 30 from a copied real
capture. The all-object gate must reject it despite sixty normal presentations
and shutdown, while preserving the original trace unchanged.
`ExitPolicy.Test.py` damages copied real stock-exit evidence in sixteen ways,
including ordinary or unidentified partial exits, changed scenario or staged
script bytes, absent reference, wrong profile/math, forged or missing assertions,
missing core/SDK background vessels, ports or ticks, nonzero exit, incomplete
teardown and an overwritten save. The original capture remains unchanged.

## Startup rejection regressions

`failure_paths.py` selects every signal-terminated scene from a preserved full
sweep, verifies its original locked scenario bytes and requires that the
negative fixture still has unavailable dependencies. It runs each unchanged
scene with both engine C and C++ sources instrumented, requires the original
dependency error and exit code 1, rejects sanitizer findings and checks normal
context deletion with zero presentations. It also exercises missing-class
creation through both the legacy and extended SDK signatures.

```sh
python3 -B Tests/Production/StockScenarios/failure_paths.py \
  --dependencies out/phase6-wayland-input-tools-final \
  --build out/phase6-vessel-dock-records-asan-engine \
  --assets out/phase6-dg-resources --data out/native-celestial-data \
  --planets out/archive-data \
  --baseline-report out/phase6-base-stock-full-smoke/stock-scenarios.json \
  --library-directory out/phase6-fontconfig-heap-pointers/build \
  --library-directory out/phase6-mesa-wayland-verified/install/lib/x86_64-linux-gnu \
  --output out/stock-startup-rejections
```

Use the independently qualified private Fontconfig and Wayland-capable Mesa
libraries described in [WindowingLifetime.md](../../../Docs/Production/WindowingLifetime.md).
The runner owns a private compositor and records source, executable and library
hashes. Run outside a LeakSanitizer ptrace sandbox, with fresh output. It does
not modify system libraries or any accepted reference. `--scenario` selects a
previously crashing case for diagnosis; omitted, all recorded crashes run.
The report explicitly keeps every stock scenario failed. Clean error handling
does not supply its missing module or qualify the complete scene.
