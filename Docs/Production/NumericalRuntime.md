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
cannot consume it. Windows calls its existing `std::rand`/`std::srand`. An
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
