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
The original Windows source copies stay unchanged. The diagnostic capability
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

Fresh repaired execution and unchanged
Dragonfly scene checks, sanitizer teardown, panel/input and persistence
checks, repeated sessions and matched four-profile Windows/native state/camera/
full-frame comparisons still have to pass. Normal class admission and Phase 6
completion remain unchanged. The Windows reference workflow now also watches
the actual Dragonfly and renderer source inputs, so a target-ownership repair
cannot leave its reference candidate stale.
