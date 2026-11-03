# Original station capabilities and native base textures

The local Release automatic host now runs the original configuration-defined
Mir and Wheel in seven complete unchanged stock scenarios. All fourteen native
runs pass the preserved Windows state, capability, docking-port, camera,
projection and full-frame comparisons. This is a local qualification within
the ongoing Phase 6 work.

The original application, SDK and graphics client remain pinned to
`f725194209634f7fd5d1d44d426cfa9b5e303e37`. Windows
[run 41658484386](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41658484386)
captures each scenario twice in Debug/Release automatic/SSE2: 56 processes,
3,360 presentations and 11,224 finalized all-vessel observations. The four
downloaded archives match GitHub's SHA256 digests. The independent audit finds
exact deterministic repeats, zero Debug/Release state errors within each CRT
profile and image SSIM 1.0. Existing accepted references are unchanged.

The native comparisons retain every declared vessel and local docking port at
ticks 0 through 60. Maximum position, rotation, angular-velocity and MJD errors
are zero; maximum velocity error is 1.83e-11 m/s. Capabilities and docking
parameters match exactly. Final camera transforms and projected object positions
match exactly. Projection checks include front-facing objects outside the image;
the Venus horizon view has no object centers inside its viewport. Full images
remain unmasked and use the existing 0.98 SSIM limit.

| Unchanged scenario | Full-frame SSIM, both native repetitions |
| --- | ---: |
| Challenge 2 - Lunar transfer | 0.999884 |
| Challenge 3 - Advanced lunar transfer | 1.0 |
| DG and DG-S | 1.0 |
| Venus takeoff | 0.999646 |
| TransX Earth to Moon | 1.0 |
| The Solar System / Venus | 0.984607 |
| Cloud microtexture | 1.0 |

The host admits those two class names only with the observed version-0
configuration-defined implementation, focus eligibility, mesh/resource/dock
counts, mass, size, inertia, cross sections and transponder state. A declared
module remains mandatory. Five real startup controls reject changed mass,
changed cross sections, a required missing module, an unknown configuration-only
clone and a wrong declared module. All fail before scene presentation and delete
their contexts normally; original assets remain unchanged.

The initial native DG-and-DG-S image scored 0.964026 because the base buildings
had no facade/roof textures. The native host omitted the original
`Base::CreateStaticDeviceObjects()` call. It now initializes these shared
resources before the original world setup and destroys them after graphics
session closure, following the Windows order. Generic base slots preserve the
original nullable day/night-texture contract; required mesh/application textures
retain their checks. The repaired ground image is byte-identical to Windows.
Twenty real scene load/unload cycles in one process complete all presentations
and context deletions. This normal-build test does not establish sanitizer
coverage.

Two earlier capture attempts incorrectly expected renderer keys named
`width`/`height` and a harness-generated `loaded-maps.txt`. The final driver uses
the renderer's actual `client_width`/`client_height` and `renderer-modules.txt`.
Those failed attempts are retained and excluded from qualification.

The new complete stock sweep has 44 clean passes and 113 failures. The remaining
112 dependency-incomplete cases and GeneralApiTest assertion remain failures;
25 of those dependency cases terminate by signal in both the old and new
baselines. They require investigation and cannot count as explicit graceful
failure or successful initialization. The restored-texture runtime also passes
the renewed complete hardware performance matrix. Wider module/scenario
acceptance, current four-profile hosted native comparison, sanitizer coverage
and durable evidence storage remain open.

[Machine-readable evidence and hashes](StockStationsVerification.json)
[Capture, comparison and negative controls](../../Tests/Production/StockVessels/README.md)
[Complete stock readiness](StockScenarioReadiness.md)
