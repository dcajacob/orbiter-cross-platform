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
the real native copies, then rejects six in-memory changes to thermal state,
physical size, attitude, original GL commands, state initialization and include
bindings. The original and generated trees must remain unchanged throughout.

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

All nine original translation units and the actual native drawing implementation
passed syntax compilation in the retained development v3 record. The complete
fresh module build, unchanged Dragonfly scenes, sanitizer teardown, panel/input
and persistence checks, repeated sessions and matched four-profile Windows/native
state/camera/full-frame comparisons still have to pass. Normal class admission
and Phase 6 completion remain unchanged.
