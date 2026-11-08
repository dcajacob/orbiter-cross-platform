# Production numerical runtime

The native engine uses an internal mathematical runtime and a private simulation
random stream. Windows retains its original CRT adapters. This change binds
existing calculations to reproducible primitive operations; it does not replace
the propagation, atmosphere, contact or autopilot implementations. Frozen flight
references and their original budgets remain authoritative.

## Root cause and evidence

The two former ground-flight failures had two causes. Identical double inputs
produced one-ULP differences in Windows versus glibc transcendental functions.
After matching those functions, the first position/velocity difference moved
from tick 2 to tick 956. Separately, the engine's calls to the process-wide RNG
depended on its platform algorithm and on draws by graphics libraries. This
changed `Body::updcount`, which determines when the existing increment
accumulation is folded into the base state.

The [original Windows observer](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41382988661)
read initial counters ISS=50 and PB=0. Its physical traces remained byte-identical
to the original reference. The old native process initialized them to 14 and 47.
An engine-owned stream reproduces 50 and 0 without assigning counters or altering
the original `irand(100)` expression, flush schedule, formulas or stage ordering.

The earlier [intermediate-force observation](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41380213246)
also proved both flights' physical, input, propellant and animation traces
byte-identical before accepting diagnostic values. Experimental process-wide
interception was used only in ignored diagnostic builds. It is not shipped.

## Native bindings

The selective [AMD source import](../../Extern/ReferenceMath/README.md) is
MIT-licensed and pinned by commit and hashes. Raw upstream files retain their
notices and remain unchanged. The build converts private MASM syntax to ELF/GAS
and supplies native error/type bindings. The import covers double sine, cosine, arcsine, two-argument arctangent and
exponential, with their coefficient tables and range reduction.
Domain errors, signed zero and NaN/exception propagation have native handlers.

The compiler/linker binds these functions only in numerical SDK consumers.
No ordinary libc math symbol is exported or globally intercepted; the separate
renderer and foreign libraries retain their own mathematical runtime. The
backend automatically selects FMA3 when AVX/FMA are available, otherwise SSE2.
`-DORBITER_MATH_FORCE_SSE2=ON` forces the baseline CPU path for qualification.
The Release equatorial latitude conversion in `Body::LocalToEquatorial`
selects the SSE2 arcsine on both CPU profiles to match original Windows Release.
The Debug conversion uses ordinary profile dispatch. The primitive test also
checks the original captured latitude input and both configuration results.
The supported initial toolchain is GCC on Linux x86-64.

Native simulation randomness uses the original runtime's unsigned 32-bit
recurrence, 15-bit result range and per-thread state. Host-library random draws
cannot consume it. The source-ported OpenGL client explicitly shares this stream
through its private renderer binding, preserving the original Windows CRT
relationship. Windows calls its existing `std::rand`/`std::srand`. An
exhaustive inverse source check recovers the pre-change eight calculation files
by undoing only the explicit RNG names and include.

Every native evidence directory records the selected math backend, RNG profile,
range and process seed in `numerics.json`. The SDK identifier also includes
backend inputs, compiler settings and the forced-profile option, so modules and
renderer must be rebuilt against the matching engine SDK.

## Qualification

The [primitive corpus](../../Tests/Production/Math/Reference/README.md) retains
28,800 original Windows observations per CPU profile. These are additional
primitive oracles, not regenerated flight references. Local tests match all
57,600 observations exactly and independently check 6,191 cases per profile
against MPFR at both 256 and 512 bits, allowing at most one ULP. Edge checks cover
signed zero, domain errors and NaN payload/exception handling.

```sh
cmake -S Src/Orbiter/Production/Math -B out/native-math \
  -DCMAKE_BUILD_TYPE=Debug
cmake --build out/native-math --parallel 4
ctest --test-dir out/native-math --output-on-failure
```

The standalone tests require MPFR development headers/library (`libmpfr-dev` on
Ubuntu); the application does not depend on MPFR. Reports record the loaded
oracle library version, path and hash. Local results are separate from hosted
qualification. The full hosted actual-client suite now passes in Debug and
Release with automatic and forced SSE2 dispatch, together with the preserved
Windows application/SDK/client/reference checks.
[NumericalRuntimeVerification.json](NumericalRuntimeVerification.json) records
the source revisions, actual profiles, measured errors and verified artifact
digests. Current flight results and remaining gates are tracked in
[GroundFlight.md](GroundFlight.md).

The exact Station building save reload exposed a missing renderer binding.
Original OpenGL particle initialization makes 3,000 random draws; native had
sent those calls to glibc instead of the numerical stream. The resulting body
counters differed before flight. Windows folded Module2A increments at tick 903;
the first public position difference followed at 904 and changed a saved decimal
digit. Passive off/on diagnostics reproduce all original simulation/frame/save
bytes before their internal observations are used. The private renderer adapter
now uses the existing engine generator and its original range for particle and
exhaust randomness. Formulas, draw order, integrator and serialization budgets
remain unchanged. A focused regression uses the five captured startup counters;
fresh complete-scene qualification remains required.

The 8 November 2026 Phase 6 campaign exposed the shared renderer binding being
applied to the external-view host as well as the complete cockpit host. Its
particle initialization consumed 3,000 simulation draws before body creation,
changing ISS/PB startup counters from the frozen external-view reference's
50/0 to 98/11. The changed accumulation timing caused the controlled-flight
fuel and uncontrolled-impact attitude comparisons to exceed their existing
budgets. A read-only startup probe and an isolated renderer diagnostic reproduced
the failure and passed both unchanged flight comparisons after separating the
visual draws.

Each native host now declares renderer ownership at process startup. The
external-view host uses an isolated, engine-owned renderer stream with the same
MSVC recurrence and range. The complete cockpit host retains the original shared
application/client stream needed by the Station building reload. The simulation
recurrence, body counter expression, accumulation schedule, physical calculations
and frozen references are unchanged. `numerics.json` records `renderer_random`
alongside the existing math and simulation RNG identities. The existing original
CRT and Station building tests remain intact; added controls preserve the
external-view counters, independent stream resets and restored shared ownership.
Fresh hosted qualification and independent final-candidate audits remain required.
