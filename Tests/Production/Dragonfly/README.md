# Original Dragonfly native integration

`source_audit.py` preserves the original 23 source/header/resource files from
`f725194209634f7fd5d1d44d426cfa9b5e303e37`, with the explicit ADI context and
bitmap-target ownership repair. All physical, internal-system and attitude
calculations and original GL drawing commands remain.

`prepare_native.py` generates separate native copies of the complete original
module from immutable producer inputs. The native copies bind SDK widths,
include casing, drawing resources, file paths and actual module ownership.
Only the original Windows DllMain and unused window-message dispatcher leave
the copies; their full original bodies are pinned by the independent reader.
The preserved Windows C++ sources and public SDK layouts remain unchanged.

`native_source_audit.py` independently reverses the declared bindings and
compares every original C++/header token stream, including literals and command
ordering. It does not import the generator. `NativeSource.Test.py` first checks
the real native copies, then rejects nine in-memory changes to thermal state,
physical size, attitude, original GL commands, state initialization and include
bindings, plus missing/nonvirtual native system and warning-list destruction. The original and
generated trees must remain unchanged throughout.

The real native drawing bindings use renderer surfaces, raster Sketchpads and
owned fonts, pens, brushes and bitmaps. The original 28 embedded BMP resources
are delivered byte-for-byte at explicit resource-ID installation paths by
`Atlantis/stage_assets.py`. Original ADI GL commands execute in a renderer-owned
compatibility context with a true color renderbuffer, then transfer the real
pixels into the panel surface. A renderbuffer keeps the original fixed texture
name 1 from replacing the target's color storage. The same ownership repair is
applied to the Windows WGL target; its expanded hosted control remains pending.

The prior native instrument package at
`e8c0246aba59c4f2022239f811e6b99ffeb320e2` passed an actual GPU control during
a complete unchanged 960-frame SolarSail scene. The control checked three real
contexts, seven restorations, two original-style display lists, 25,736 pixels,
pixel transfer state and the texture-name collision. All 15 compared original
scene state/resource/mesh/playback/camera/full-frame/lifecycle files were byte
identical to the earlier native capture. The record is
`out/phase6-native-instrument-control-audit-v1.json`. This control establishes
target ownership and regression evidence; it does not qualify Dragonfly raster
parity, interaction or lifetime behavior.

The complete fresh Debug ASan/UBSan module and renderer package at
`dc63207202722bb2efc1b8422c352251ab2b38a5` passed all four actual build stages,
with 767 source/dependency inputs guarded. Its record is
`out/phase6-dragonfly-native-Debug-asan-v1/build.json`. All 28 original panel
bitmaps are delivered in the 1,130-file resource tree. The stager also supports
isolated worktrees on another filesystem by copying when hard-linking returns
EXDEV. The first failed staging tree is retained separately.

All five complete unchanged Dragonfly scenes then failed during real module
initialization. UBSan identifies a Valve member access whose actual object
table belongs to the engine's unrelated scenery Tank. Both the original vessel
module and actual engine export the same ELF Tank class-table/typeinfo names.
The private native module now hides its C++ implementation symbols while its
checked OrbiterNativeQuery entry remains exported. The builder checks the actual
DSO's dynamic symbols for this collision. Every original calculation remains
unchanged. No sanitizer checks are suppressed.

The failed captures, all 57 actual data-file hashes and the exact 794 owning
source inputs are retained in `out/phase6-dragonfly-native-smoke-v1` and
`out/phase6-dragonfly-source-dc632-v1`.

The second fresh package at `dd41f811a9cb8dd88cdcf5a76a2b8717ab9ede8a`
also passes all four build stages, with all 767 inputs unchanged. Actual DSO
inspection proves that Dragonfly no longer exports the conflicting tank class
table, typeinfo or methods, and its checked factory remains exported. The engine
retains its actual scenery Tank symbols. The independent record is
`out/phase6-dragonfly-symbol-isolation-v1.json`.

All five original scenes get past that collision, then ASan stops the actual
electrical-system list's destruction: it deletes a 184-byte FCell through a
104-byte nonvirtual e_object base. The hydraulic owning list has the same
nonvirtual-base deletion. Both base classes are already polymorphic. The native
copies now gain default virtual destructors so the existing deletion calls use
each allocated concrete type. The independent source reader requires exactly
those declarations and conserves every original simulation body and field.
The frozen Windows baseline stays unchanged. The diagnostic capability
check also accounts for all eleven original vent jets/tanks created before the
fourteen RCS thrusters and main propellant resource. Those resources are part
of the preserved source, not additions to the simulation.

The second failed capture, all 57 actual data inputs and all 794 owning sources
remain in `out/phase6-dragonfly-native-smoke-v2` and
`out/phase6-dragonfly-source-dd41-v1`.

The third fresh package at `2e5e2c3782eb7464a0c9f11c5577324d4fdbd52f`
builds and clears the polymorphic deletion error. Its unchanged external scene
then rejects the diagnostic capability check: the Dragonfly module derives
from VESSEL2, whose actual SDK interface version is 1. The check incorrectly
required 2 and is corrected. Cleanup also reports 888 bytes in 37 allocations;
those leaks remain failures. The terminal capture and exact sources are
`out/phase6-dragonfly-native-smoke-v3` and
`out/phase6-dragonfly-source-2e5e-v1`.

The observation probe now forwards the original complete SetClassCaps call once,
then reads the actual capabilities and current process mappings. This preserves
allocation-address evidence even if an early scene failure unloads the module
before LSan runs. It sets no vessel state and changes no simulation callback.
The bitmap resource stager separately verifies the original resource.h ID
definitions as well as panel.rc and each raw BMP.

The fourth package at `3e47a10c06e6b1787f8a7570706080201cda56ba` builds
and directly observes Dragonfly's original capabilities: SDK version 1, empty
mass 7,000, size 4, one mesh, 25 thrusters, 12 propellants and one dock. The next
initialization failure is the native oapiBlt bridge rejecting its obsolete
color-key argument. The original Windows API warns once, ignores that argument
and always performs the default rectangle copy. The native bridge now follows
that original contract. An added GPU control requires all 45 copied pixels,
including a black pixel with ck=0, in addition to the previous target controls;
its fresh execution remains pending.

The captured pre-unload module mappings resolve all 37 leaks to the exact
original `CW::Watch(new bounds(...))` allocation statements: 888 bytes total.
The record is `out/phase6-dragonfly-watch-list-leak-audit-v1.json`. The native
warning destructor now deletes its owned list before the original surface
release. Every monitoring threshold, comparison, allocation and update remains
unchanged. The fourth failed capture and exact source tree remain in
`out/phase6-dragonfly-native-smoke-v4` and
`out/phase6-dragonfly-source-3e47-v1`.

The builder now independently verifies the complete generated source tree after
configuration and after each actual build stage, retaining every generated raw
input hash. The capture runner guards those exact generated files alongside the
original sources, runtime and probe through process exit. This closes the gap
between verifying the generator's inputs and retaining its actual compiler inputs.
The first invocation of that stricter check is retained as a failed v5 build:
JSON reads resource-ID pairs back as lists, while the in-memory provenance used
tuples. The schema now explicitly creates JSON arrays. `PreparedSource.Test.py`
exercises a real fresh preparation and read-only round trip, then requires
physical-source and resource-ID provenance damage to fail without rewriting
either valid or damaged inputs. The fresh build still has to pass that check.

The fresh v6 package at `83c025ecdaf383cc963aa36ec798fdd667023536`
passes all four build stages with 768 immutable source/dependency inputs and
68 actual generated compiler inputs verified before and after compilation.
The real preparation/JSON round trip and both damaged-copy controls pass in
`out/phase6-dragonfly-prepared-source-controls-v1`.

All five complete unchanged Dragonfly scenes now complete once: 4,800 real
presentations, five clean graphics teardowns and no ASan/UBSan/LSan findings.
The external-scene record is `out/phase6-dragonfly-native-smoke-v6`; the four
cockpit scenes are in `out/phase6-dragonfly-native-cockpits-v1`. Their independent
post-exit audits are `out/phase6-dragonfly-first-clean-runtime-audit-v1.json` and
`out/phase6-dragonfly-four-cockpits-audit-v1.json`. The actual instrument control
also passes all 25,781 pixels and the original obsolete-argument copy during a
complete unchanged SolarSail scene. All 15 compared state/resource/playback/mesh/
camera/full-frame/lifecycle files remain byte-identical to the earlier native
SolarSail capture. No scene or input resource is changed.

The same-process PoweredUp control passes two real 60-frame sessions. The
loader trace records two actual Dragonfly link-map creations, initializations,
finalizations and destructions. Both contexts close cleanly, all six compared
session state/control/camera/full-frame outputs are byte-identical and the
sanitizers report no findings. The record is
`out/phase6-dragonfly-inprocess-cycles-v1/verification.json`. This is a separate
short lifetime control; it does not replace the full-scene repeat requirement.

The hosted renderer probe still expected rejection of the obsolete oapiBlt
argument. That assertion contradicted the original SDK contract and stopped
the later Shuttle-A captures. It now requires exact copied pixels with the
requested key matching the source background and a different destination fill.
The same updated probe fails the actual old bridge and passes all twenty real
context cycles on the corrected bridge: 5,120 legacy-copy pixels plus the
existing glyph, dimension, overlap, reference, opacity and compressed-target
controls. Both historical runtimes and caller-header identities are retained in
`out/phase6-legacy-copy-renderer-regression-v1/verification.json`. Hosted
verification remains pending. CI explicitly installs the GLU development
dependency required by the original instrument commands.

All five complete unchanged scenes now also pass twice in native Debug automatic:
ten clean processes, 9,600 actual presentations, 34,596 vessel-state rows and
identical repeated state/resource/playback/mesh/camera traces and full frames
(SSIM 1.0). The post-exit audit rehashes all 520 process evidence files, 896
source/runtime/probe guards, 68 generated compiler inputs, 1,130 staged assets
and all 57 actual kernel/gravity/planet inputs. The records are
`out/phase6-dragonfly-native-complete-v1` and
`out/phase6-dragonfly-repeat-audit-v1.json`; the matching source snapshot is
`out/phase6-dragonfly-source-83c025ec-v1`.

Fresh repaired Windows execution, panel/input and persistence checks, broader
repeated sessions and matched four-profile Windows/native state/camera/
full-frame comparisons still have to pass. Normal class admission and Phase 6
completion remain unchanged. The Windows reference workflow now also watches
the actual Dragonfly and renderer source inputs, so a target-ownership repair
cannot leave its reference candidate stale.

The read-only SDK clock observer at `3d582560` also completes unchanged
PoweredUp and Spin stabilisation scenes twice: 3,840 presentations, four clean
teardowns, 212 rehashed process evidence files and all original gates retained.
Both native traces end at system time 14.983125000000001 and simulation time 15;
neither reaches the original system-time script's later warp change. All twelve
compared PoweredUp state/resource/playback/mesh/camera/frame/lifecycle outputs
remain byte-identical with the extra clock getters. Eight damaged clock copies
are rejected for each of the four actual executions. The audit and frozen
observer/runtime source inputs are in
`out/phase6-remaining-stock-sdk-clock-audit-v1.json` and
`out/phase6-remaining-stock-source-3d582560-clock-v1`.

The old repaired Windows Release/SSE2 PoweredUp mismatch is now reproduced with
the real v6 native module. Varying only ASan's allocation fill between zero and
255 reproduces the good and bad Windows runs exactly for all thirteen observed
TUG mass/fuel snapshots and twenty-six waste-vent rows over twelve real frames.
The bad Windows save has a waste tank with negative mass and NaN temperature;
the good save is finite. Read-only debugger observations at the first actual
`FCell::Cloging` call show `Amperes` still carrying the allocation-fill bits
(`0xbebebebe`, or NaN with `0xffffffff`). The constructor never assigned it,
and the thermal expression reads it before the normal update assigns current.
Both short allocation-pattern executions return zero, close their graphics
contexts and produce no ASan/UBSan/LSan diagnostics; those sanitizers do not
prove initialization of this field. The separate debugger observations are
intentionally terminated at the observation point and count as diagnostic
evidence only. The first debugger command-format failure is retained as v1.

`out/phase6-dragonfly-fcell-initialization-audit-v1.json` records the actual
source/read evidence, original Windows saves, native controls and exact
cross-platform correlations. The historical Windows process was not debugged
at its initial read. The evidence supports the initial-current cause; it does
not turn the old failed or merely repeatable captures into accepted references.

The shared source now explicitly initializes the stopped fuel cell's previous
current to zero. The independent source audit derives exactly that one
assignment from the frozen original; every update formula, operation order and
public SDK layout stays unchanged. Windows repaired-source v2 declares this
sixth source path, independently rederives its permitted delta, and rejects
self-consistent changed/missing initialization or thermal-formula copies. The
native token reader additionally rejects changed and removed initial current.
Fresh source preparation, compilation, allocation-pattern controls, complete
scenes and four-profile Windows/native qualification of this repair are pending.
