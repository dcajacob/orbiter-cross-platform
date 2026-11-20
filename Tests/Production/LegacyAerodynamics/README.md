# Legacy axial drag

`VESSEL::SetCW` accepts separate coefficients for travel along the positive and
negative vessel Z axis. The legacy aerodynamic method weights the corresponding
coefficient by the absolute axial component of the normalized air-relative
velocity. The drag force opposes that velocity. A bank command rotates the
capsule's lift about the flight path.

## Run the force test

```sh
cmake -S Src/Orbiter/Production -B build/legacy -DBUILD_TESTING=ON
cmake --build build/legacy --target production_legacy_aerodynamics_test
ctest --test-dir build/legacy -R '^Production\.LegacyAerodynamics$' --output-on-failure
```

The fixture compiles the method body from `Vessel.cpp` against prescribed
velocity, density, coefficients and control state. With axial weights of 0.4
forward and 3.0 backward, at a dynamic pressure of 5,000 Pa it expects 2,000 N
forward-flight drag and 15,000 N backward-flight drag. Applying the same test to
the original code returns 2,000 N in the backward case and fails. Further checks
cover lateral and vertical flow, the direction of drag work, zero speed, implicit
CW and invariance of transverse lift when changing the axial drag coefficient.

## Gemini VIII flight regression

A second test flies four native Linux OpenGL entries from the phase 18 Gemini
save. It measures the effect of the engine's axial coefficient independently of
the pilot's bank command. Both paired engines use the Gemini integration
snapshot. Their legacy force method bodies match the OpenGL base and head,
respectively. Full-rate native force and state traces and final saves repeated
byte for byte for each case. The flight regression runs on staged Gemini
runtimes, while the GitHub Actions job builds the force fixture on the PR.
[Replay instructions, per-case results and binary hashes](https://github.com/dcajacob/gemini4orbiter/tree/8576adac034327ebf875aefe29cdef11f9a5797f/Native/verification/gemini8#same-save-entry-comparisons).
