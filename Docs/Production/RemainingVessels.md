# Original remaining native vessel integration

The complete original HST, solar-sail and quadcopter modules now compile against
the real native SDK and pinned Lua 5.1. Their actual forces, flight controllers,
HST keys/animations/Lua bindings and solar-sail deformation/paddle/radiation code
remain conserved by `Tests/Production/RemainingVessels/source_audit.py`: all 14
original source/header/Lua files and 12 original resources/install rules are
checked against `f725194209634f7fd5d1d44d426cfa9b5e303e37`. The declared
ownership repairs below preserve physical and drawing calculations. Public
Windows SDK and instance layouts stay unchanged.

The separate opt-in `production_remaining_stock_diagnostic` uses the actual
production session, physics, renderer, Lua and checked module factories. It
checks named original class/configuration capabilities and emits an explicit
unqualified marker. The normal executable's initial class-admission gate remains
unchanged. This work does not establish Phase 6 or complete stock admission.

The first Debug ASan/UBSan package at
`72c35b75c117c16a94b38925e90e7d1ca2812a08` is retained in
`out/phase6-remaining-vessels-native-Debug-asan-v1`. Complete unchanged solar-sail,
quadcopter and HST animation scenes each render 960 actual 1/64-second frames,
with every actual vessel, port, thruster, propellant, attachment, playback flag
and mesh observed. HST and solar-sail teardown are clean. The quadcopter's
four original rotor allocations leak: 384 bytes in four objects. Retained actual
allocation PCs resolve through contemporaneous process mappings to all four
rotor-constructor lines in
`out/phase6-quadcopter-rotor-leak-audit-v1.json`. Original failed execution and
the independent diagnostic audit remain in
`out/phase6-remaining-vessels-native-smoke-v1` and
`out/phase6-remaining-vessels-native-smoke-audit-v1.json`.

A separate real two-session solar-sail test completes both 60-frame sessions
and graphics teardowns, then LSan finds the first session's 153-node neighbor
graph and vertex buffer were replaced without deletion: 17,136 bytes in two
allocations. The exact record is
`out/phase6-remaining-vessels-solar-cycles-v2`. The earlier v1 control stopped at
an observation-clock mismatch before its second session; that failed attempt
remains retained.

The propulsion subsystem now destroys its four owned rotors. Solar-sail module
cleanup releases all index, neighbor, vertex and normal scratch caches. The
original traversal counter and deformation operations remain unchanged. The
GNU build gives this private module ordinary unloadable symbol binding, matching
GCC's documented `-fno-gnu-unique` behavior; no other DSO defines this vessel
class. [GCC Code Generation Options](https://gcc.gnu.org/onlinedocs/gcc/Code-Gen-Options.html#index-fno-gnu-unique).
The builder checks the actual exported symbol binding.

The fresh repaired Debug ASan/UBSan package at
`108c5d524b80294151f3e09e0fcfb9e08943b370` is retained in
`out/phase6-remaining-vessels-native-Debug-asan-v2`. All three complete scenes
now finish cleanly: 2,880 presents, three context deletions and 4,805 actual
vessel-state rows. The complete sampled state/resource/control/animation traces,
camera, mesh manifest and full captured frames are byte-identical to their
retained pre-repair counterparts, including the quadcopter scene before its
old exit-time leak. All 538 owning inputs, 34 additional builder/audit/dependency
inputs, actual runtime/probe bytes and all 1,102 retained asset inputs stay
unchanged during each repaired capture.

The repaired solar-sail two-session control passes with no sanitizer diagnostics
in `out/phase6-remaining-vessels-solar-cycles-v3`. The separate v4 native loader
trace records two link-map creations, initializations, finalizations and actual
link-map destructions for `SolarSail.so`, with both 60-frame sessions and contexts
completed. This verifies actual unload/reload of the module. The independent
regression audit is `out/phase6-remaining-vessels-repair-audit-v1.json`.

These are real integration and ownership results. All 38 complete scenes twice
in each required profile, independent four-profile Windows/native
state/camera/full-frame comparisons, additional Lua/input/persistence/lifetime
controls, Dragonfly native instruments and the original full Phase 6 scope
remain open. The historical complete 157-scene result remains 118 passed and
39 failed at its recorded owning source; these diagnostics do not revise it.

The complete original Dragonfly module now also builds against actual native
bitmap, Sketchpad and compatibility-context resources. Its original 28 embedded
panel BMPs are delivered unchanged. Complete-scene sanitizer execution has
identified and retained an ELF class-symbol collision and an original nonvirtual
system-list deletion; native qualification remains pending.
[Dragonfly source conservation, actual controls and retained failures](../../Tests/Production/Dragonfly/README.md)
