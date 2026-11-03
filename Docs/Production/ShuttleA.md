# Shuttle-A native integration candidate

Phase 6 now compiles the original Shuttle-A production module and its payload
in the native cockpit build. The application capability gate remains closed
pending original Windows observations and native comparisons. This does not
increase the accepted stock-corpus pass count or complete Phase 6.

The port retains the original flight and parachute calculations, resources,
animations, panel/VC instruments, attachment logic and Lua methods. The source
audit compares all 40 original implementation/header files against preserved
revision `f725194209634f7fd5d1d44d426cfa9b5e303e37`. Windows keeps its SDK
types/layouts and scenario-editor page. Native loading uses the existing checked
module ABI, with one shared drawing-resource lifetime across simultaneous ships.
The native SDK build identity includes the module sources, common instruments
and source mesh used to generate group IDs.

Native SDK adapters delegate rectangular colour fills, mesh-group insertion,
surface/texture loading and legacy panel redraw requests to the existing
production renderer and Pane implementations. Native VC bitmap resources load
the original BMP bytes from staged files. Packed RGB constants have the same
values as the original Windows macro. The Lua declaration linkage is made
consistent with its existing static definitions; method bodies are unchanged.

The new Windows observation matrix covers all six unchanged Shuttle-A scenes
and four complete DG scenes containing Shuttle-A. It preserves every declared
ship, repeats each session, records all vessel states/capabilities and docking
ports, and keeps the existing numerical and image budgets. It builds only an
observer against the preserved application, SDK and graphics client. The four
original Debug/Release automatic/SSE2 profiles must be captured and audited
before admitting native capabilities.

See [the fixture and commands](../../Tests/Production/ShuttleA/README.md).
Native state/image comparison, interactive Shuttle-A controls, payload
deployment and sanitizer lifetime checks remain pending. The Windows-specific
Shuttle-A scenario-editor page also needs a native UI implementation.
