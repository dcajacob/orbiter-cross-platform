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
The complete sweep at runtime source `9418ae29` finds 45 scenarios with their
declared configuration/module files present. Mir/Wheel now have an explicitly
qualified local Release automatic capability policy and seven formerly rejected
scenarios pass. GeneralApiTest still fails its preserved original-Windows
Earth-obliquity assertion. The 112 remaining scenarios lack staged class
configurations and their source modules. All failures remain failures: the
result is **44 passed, 113 failed**, improving the preceding `2c00d29b` baseline
of 37/120. This is not full stock acceptance. The same 25 dependency-incomplete
cases terminate by signal in both runtimes; their crash handling remains open.

Each attempted scene must complete 60 original 0.25-second frames with normal
context deletion and complete finalized ticks 0 through 60. At every tick the
actual original vessel trace must contain the entire declared ship manifest,
including non-focus ships and exact class names. Lua/runtime/sanitizer errors
are retained. Missing modules, exceptions and process failures cannot silently
turn into configuration-only successes. The current host's controlled default
epoch for missing/invalid numeric dates is recorded; this does not qualify
wall-clock Today semantics. This is an initialization/smoke sweep, separate from
interactive acceptance and additional original Windows state/image comparisons.

```sh
python3 -B Tests/Production/StockScenarios/run.py \
  --backend wayland --executable out/phase6-base-stations-engine/orbiter-production \
  --assets out/phase6-dg-resources --data out/native-celestial-data \
  --modules out/phase6-base-stations-engine/NativeModules --planets out/archive-data \
  --output out/stock-full-smoke

python3 -B Tests/Production/StockScenarios/verify.py \
  --capture out/stock-full-smoke --assets out/phase6-dg-resources \
  --modules out/phase6-base-stations-engine/NativeModules \
  --runtime-source-commit 9418ae293fc7c4cbee49538163e14d97ec3e5a1c \
  --output out/stock-full-audit.json
```

Use an owned correctness-test display, matching backend, and appropriate
runtime library path. All output directories/files must be fresh. The sweep
exits nonzero when any scenario fails and still saves every attempt. The audit
can successfully validate an incomplete sweep, but reports `audited-incomplete`
and retains all 113 failures. It never equates that status with passing the
corpus gate. `--inventory-only` and selected `--case` runs are not complete
smoke qualification.

`Inventory.Test.py` checks indented/shorthand parsing, required-module failure,
intentional configuration-defined vessels, path escape and directory-alias
rejection against temporary fixtures and all locked scenario bytes.
`Manifest.Test.py` removes a non-focus ship at tick 30 from a copied real
capture. The all-object gate must reject it despite sixty normal presentations
and shutdown, while preserving the original trace unchanged.
