# Complete remaining-stock persistence candidate

This separate candidate covers all 38 complete remaining-stock scenes, both
repetitions and all four Debug/Release automatic/SSE2 profiles. It creates no
accepted reference, native admission or Phase 6 completion. Frozen original
scenes/scripts and all existing numerical, camera and image budgets remain
unchanged. Generated saved scenarios are separate hashed inputs.

The native `--save` argument supplies the destination for a Save command; it does
not save automatically on exit. The existing real replay command at input tick
959 in phase `after` runs after finalized physics/camera tick 960. A fresh native
PoweredUp run at `45c3155d` completes 960 actual steps/presentations, executes that
Save command, returns zero and deletes the context with unsuppressed sanitizers.
Every source/runtime/generated input, all 1,130 assets and all 57 actual data
files are checked before/after. The real clock/frame observations pass fourteen
damaged-copy controls. Evidence is in `out/phase6-native-finalized-save-v1` and
`out/phase6-finalized-save-clock-controls-v1.json`.

`saved_state.py` retains every saved vessel, class and module record, plus all
camera/MFD/panel/environment blocks. It reports exact content-token differences;
it infers no numerical tolerance. Protocol-declared operator description blocks
are excluded only when a caller requests that comparison. Actual Windows output
contains three vessels and 128 vessel/module records. Two line-ending positives,
seven malformed-file controls and four changed/omitted-field controls pass in
`out/phase6-saved-state-reader-controls-v2.json`. The earlier parser accepted a
missing vessel END delimiter; that failed v1 control log is retained.

The actual Windows and native finalized-tick-960 saves have the same date,
focus, vessels and all parsed content except the ADI's last three reference
components. Two unchanged real one-frame runs vary only allocator fill 0/255
with a 65,536-byte fill limit. Both return zero with one actual presentation,
clean context destruction and no sanitizer errors. Ten physical/resource/mesh/
clock trace files are byte-identical; the only parsed save difference is the
ADI reference vector. Nonzero fill reproduces the original Windows reference.
The ADI constructor omits its transient `ref_handle` request initialization;
`PaintMe` treats any nonzero value as a user request to capture the reference.
The exact evidence is in `out/phase6-adi-request-initialization-audit-v1.json` and
both `out/phase6-adi-request-heap-*-v1` diagnostic directories.

The shared constructor now explicitly initializes that request to zero, retaining
loaded references and all original reference/attitude/drawing operations.
Windows source variant v3 declares this separately from the prior v2 fuel-cell
repair. Both source variants are independently derived from the frozen original
ADI source; old captures remain old captures.

The repaired `c4c7a231` native Debug automatic package now completes four real
one-frame controls: both allocation fills with the unchanged stock input and
both fills with the exact hashed original Windows end save. Stock references
remain zero and loaded nonzero references remain unchanged. All ten physical,
resource, playback, mesh and begin/end-clock trace files, and all parsed saved
content, are identical between each pair. Every process returns zero with one
successful presentation, clean context destruction and unsuppressed sanitizers.
A separate repaired 960-frame native Save run also returns zero; its ten traces,
camera, framebuffer and complete saved content are byte/content-identical to
the earlier default-allocation native run. The independent audit rechecks 769
source/dependency files, 96 runtime/generated files, 1,130 assets and 57 actual
data files. Evidence is `out/phase6-adi-request-fixed-audit-v1.json`; the exact
837 source/dependency/generated streams are retained in
`out/phase6-adi-request-source-c4c7a231-v1`. Fourteen damaged actual clock/frame
copies are rejected in `out/phase6-finalized-save-fixed-clock-controls-v1.json`.

`saved_inputs.py` names each exact Windows save beneath `_Phase6Persistence`,
keeps the original recording basename and retains every saved vessel/class.
The source save's raw hash is mandatory: even transport-newline changes are
rejected as a different reload input. `SavedInputs.Test.py` uses actual Windows
outputs to reject changed parents, classes, fields and line endings. Four real
saved inputs and twenty damaged-copy controls pass locally in
`out/phase6-exact-saved-input-controls-v2.json`; these historical v2 saves test
the reader only and are not relabeled as repaired v3 observations.

`capture_windows.py` first independently verifies the complete original
application/SDK package, repaired v3 module/runtime/source closure and actual
parent observations. It then reloads every exact saved input in fresh processes,
using the unchanged 960-frame matched-clock policy, real framebuffer, all-vessel
state/resource/mesh/playback observations and original numerical/camera/image
budgets. Every original recording and simulation-data byte remains guarded.
The diagnostic workflow selects PoweredUp/Spin explicitly; the full workflow
selects all 38 scenes, both original repetitions and all four Windows profiles.
Both workflows retain the separately named input saves and reload outputs.
They await actual Windows execution; adding collection is not a runtime pass.

```sh
python -B Tests/Production/RemainingStockPersistence/capture_windows.py \
  --parent-capture out/remaining-stock-repaired \
  --build out/remaining-stock-repaired-build --preserved out/remaining-stock-preserved \
  --data out/production-data --planets out/standard-planets --mesa out/mesa-runtime \
  --configuration Debug --math-profile automatic --output out/remaining-stock-persistence
```

Fresh corrected Windows writers, complete native/Windows reload comparisons,
all four native profiles, control and lifetime checks are still required.

All four fresh native packages at `e3f3735d` now complete their immutable build:
Debug/Release, automatic/SSE2, each with ASan/UBSan and independently checked
generated sources. `capture_native.py` collects either `--phase stock-writer`
or `--phase windows-save-reload`, with all 38 scenes and both repetitions by
default. Both execute the real Save command after finalized tick 960, retain
complete state/resource/mesh/playback/camera/frame outputs and compare repeats
under the unchanged budgets. The reload phase independently checks the Windows
source/runtime and full preserved original package before copying each exact
saved input. A selected case list is explicitly diagnostic-only; missing startup
configuration evidence is forbidden for the complete reload campaign. Both
native phases remain required for qualification.

Two repaired Windows diagnostic profiles at `c4c7a231` are independently checked
in `out/phase6-windows-adi-request-initial-audit-v2.json`: eight actual processes,
7,680 presentations and 112 recorded damaged-clock/frame controls. The original
1,037-file Debug and 925-file Release packages, repaired v3 sources and actual
replacement/build bytes pass their independent checks. PoweredUp's complete
parsed saved content now matches the repaired native writer exactly in both
profiles, excluding only the protocol's operator-description blocks; state,
camera, actual clocks and full-frame image comparisons also pass. These are
two-scene diagnostics and one native Debug automatic comparison, not the full
four-profile/all-scene qualification.

That audit exposed a separate validation defect: the full reader compared
`Orbiter.cfg` after execution to the initial fixture, but the conserved original
`Orbiter::Launch` and `SaveConfig` call `Config::Write`. The actual file is the
normal rewritten master configuration. The retained failed v1 audit records
that incorrect comparison. New runs copy the actual startup bytes to
`staged-Orbiter.cfg` before execution and hash the separate snapshot in the
invocation. The full gate checks that exact startup input against the complete
frozen fixture and still checks/retains the actual rewritten output. Ten
coherent-hash/descriptor/physics/format controls pass on a separately labeled
reader fixture made from retained native startup and Windows rewritten files;
this fixture executes no simulator and is not Windows runtime qualification.
The native collector and repaired Windows workflows run those controls again
on their real newly captured startup inputs. Historical captures without a
startup witness remain historical and cannot satisfy the new complete gate.
The new persistence protocol specifies reloading the same exact Windows save in
both runtimes, alongside separately checking the native writer at measured
original serialization precision. It does not convert a scoped reader or save
experiment into full persistence acceptance.

The fresh Release reload diagnostic also exposes an inherited gauge-label
storage overflow before the first frame. GDB identifies the actual `PITCH`
copy into `EGauge::unit[5]`. Source variant v4 enlarges only that private buffer
to the exact original longest label plus its terminator (six bytes), with
unchanged strings, arithmetic and drawing. Complete persistence collectors now
require v4; explicit native diagnostics can read historical v3 inputs and
record that source identity. Repaired Release execution and full qualification
remain pending; the failed v3 processes remain retained.
