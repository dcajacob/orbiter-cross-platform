# Original remaining native vessel modules

The source audit conserves all 14 original HST, solar-sail and quadcopter
source/header/Lua files and all 12 original resources/install rules from
`f725194209634f7fd5d1d44d426cfa9b5e303e37`. Platform changes bind the same
fixed-width SDK types, case-insensitive text helper, portable include paths,
private file-local Lua declarations and checked native factories. All original
HST animations/keys/Lua methods, solar radiation/paddle forces and elastic mesh
deformation, and quadcopter rotor forces/flight controllers/Lua methods remain.

The native modules link the actual SDK and pinned Lua 5.1 with undefined symbols
forbidden. Their complete sources, generated mesh IDs and factory dependencies
enter the native SDK fingerprint. Windows retains its real SDK and original
module entry points and layouts.

`build_native.py` requires fresh outputs and immutable Git producer inputs,
protects every extraction/dependency source and archive during the build, and
records exact commands, CRT/math/sanitizer flags, modules, host and generated
compiler inputs. A separate opt-in `production_remaining_stock_diagnostic`
host checks named original module/configuration capabilities, emits an explicit
unqualified marker and retains the real session/physics/rendering code. Production
admission remains unchanged. The new modules await actual build/runtime and
ASan/UBSan/LSan checks, full unchanged scenes, Lua/input/persistence/lifetime
controls and matched four-profile Windows/native state/camera/full-frame gates.
Dragonfly native instruments and all other Phase 6 scope remain open.

```sh
python3 -B Tests/Production/RemainingVessels/source_audit.py
```
