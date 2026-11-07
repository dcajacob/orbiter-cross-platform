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
admission remains unchanged.

`paused_attachments.py` exercises the complete unchanged three-vessel Atlantis
ISS-resupply scene without a preload observer. It keeps simulation time at zero,
uses real F5 keys to replace the world up to nineteen times, then closes normally.
Every world must retain ISS docking and both Leonardo attachment links, render
at least sixty frames, preserve all three finite vessel states and delete its
graphics context. ASan, UBSan and unsuppressed LSan must remain clean. Original
scene bytes seed F5; this is lifetime coverage, not actual-save persistence or
flight parity. `--expect-use-after-free --worlds 1` instead requires the original
paused-shutdown failure from an identified old package. Supply the package,
staged assets, celestial data, planet archives, private compositor tools,
decoration plugin and library paths explicitly; `--help` lists the arguments.
See [the attachment cleanup record](../../../Docs/Production/AttachmentTeardown.md).

The same `native.py` entry point accepts `--lifetime-sessions 20 --owner PATH`
for selected twenty-world ownership diagnostics on an immutable package in a
separate checkout. Supply its usual build, build-record, assets, data, planet,
compositor, pinned decoration/provider and output arguments, plus explicit
`--case` IDs and at most four `--jobs`. This mode uses the complete original
scenarios, sixty fixed-step frames per world, an empty original-dispatch replay,
and actual module initialization, finalization and link-map destruction records.
It preserves every world's state, camera and full frame, checks all original
vessels, actual math mode, clean graphics and unsuppressed sanitizers, and records
the simulator's owned PID/start/exit receipt. It does not qualify interactions,
persistence, normal admission or stock parity. Independently re-read closed
captures with `lifetimes.py --capture PATH/lifetimes.json --output FRESH.json`.
`Lifetimes.Test.py` rejects incomplete ticks, substituted or lost vessels,
nonfinite state, truncated frames, incomplete graphics and retained modules.

`native.py --capability-control` uses the same immutable package/provider setup
for short actual SDK snapshots. Declare the matching `--windows-reference`
capture, `--windows-build` and `--preserved` original package. Each selected case
runs with the passive observer off and on, preserving all original vessels.
Actual fields and ports are compared with the hashed Windows observations;
native state, camera, controls and complete frames must remain equivalent.
The observer's existing getters and forwarding remain byte-conserved, with only
an explicit diagnostic switch around its old wall-clock delay. Normal capture
keeps that delay. Exact local docking comparisons and existing physical/image
budgets remain in force. Re-read closed captures independently with
`capabilities.py --capture PATH/capabilities.json --output FRESH.json`.
These sixty-frame diagnostics earn capability/observer scope only. They do not
qualify full stock parity, persistence, interactions or normal class admission.

The first fresh Debug ASan/UBSan package at
`72c35b75c117c16a94b38925e90e7d1ca2812a08` builds all three actual modules and
both diagnostic hosts. Its record is
`out/phase6-remaining-vessels-native-Debug-asan-v1/build.json`: 538 owning inputs
and 32 additional builder/audit/dependency inputs. The complete unchanged solar-
sail and HST animation scenes each capture 960 real 1/64-second frames cleanly,
recording every actual vessel, resource and mesh. Their real screenshots are
under `out/phase6-remaining-vessels-native-smoke-v1`. The whole-scene diagnostic
audit is `out/phase6-remaining-vessels-native-smoke-audit-v1.json`.

The quadcopter completes the same 960 frames and context teardown but LSan finds
four lost 96-byte rotors. Its retained allocation PCs and original process maps
resolve all four allocations to the propulsion constructor in
`out/phase6-quadcopter-rotor-leak-audit-v1.json`. The subsystem now deletes its
four owned rotors. All rotor forces and flight-controller calculations remain
unchanged.

A separate two-session complete solar-sail scene reproduces a 17,136-byte loss
in two allocations: the first 153-node neighbor graph and vertex scratch buffer
are replaced without release. Both sessions complete 60 real frames and clean
graphics teardown; LSan fails at process exit. Exact inputs, source/runtime
hashes and console remain in `out/phase6-remaining-vessels-solar-cycles-v2`.
The earlier v1 attempt stops at an observation-clock mismatch before session 2;
it remains failed evidence.

The module now owns and releases its index, neighbor, vertex and normal scratch
caches on final release. The original traversal code and every deformation
operation stay unchanged. The GNU build uses `-fno-gnu-unique` for this private
module so actual `dlclose`/`dlopen` resets ordinary module static state. The first
binary's sail-index symbol had GNU-unique binding; GCC documents its effect on
unloading in [Code Generation Options](https://gcc.gnu.org/onlinedocs/gcc/Code-Gen-Options.html#index-fno-gnu-unique).
The builder checks the new module's actual exported symbols for that binding.
No instance layout or public Windows SDK changes.

Fresh sanitizer execution, exact before/after state and frame comparisons,
repeated-session controls, all complete unchanged scenes, Lua/input/persistence
checks and matched four-profile Windows/native state/camera/full-frame gates
remain required. Dragonfly native instruments and all other Phase 6 scope remain open.

```sh
python3 -B Tests/Production/RemainingVessels/source_audit.py
```
