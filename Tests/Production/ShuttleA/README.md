# Shuttle-A production port and original observations

The native cockpit build compiles the original Shuttle-A vessel, all panel
instruments, its Lua methods and the original parachute payload. Native module
factories use the checked SDK build identity. Shared drawing resources are
created for the first ship and released after the last ship is destroyed.
The comparison candidate admits only the initial capabilities observed in the
audited Windows matrix. Native support remains unqualified until its state,
image, input and lifetime gates pass.

`source_audit.py` compares all 40 original source/header files against the
preserved application revision, allowing only declared platform adaptations.
It conserves the flight equations, capability values, animations, attachment
logic, payload parachute dynamics, instruments, Lua bodies and callback order.
The full extraction audit invokes this check too.

`cases.json` pins all six complete Shuttle-A scenarios and four complete DG
scenes containing Shuttle-A: Mk4 in orbit, Virtual cockpit, DG-S ready for
takeoff and Docked at ISS. Every background ship remains present. It also pins
the original source resources. Clocks, numerical budgets and the full-frame
SSIM threshold are inherited unchanged from the accepted cockpit fixture.

The shared StockVessels observer supports `--suite shuttle-a`. It records every
vessel and docking port at finalized ticks 0 through 60 and repeats each scene
twice. The separate `original-shuttle-a.yml` workflow uses the preserved Windows
application, SDK and client binaries in Debug/Release automatic/SSE2 profiles;
it builds only the public SDK observer. Existing captures are never replaced.
Its omission controls must reject a missing background vessel and docking-port
row while leaving the original trace hashes intact.

```sh
python3 -B Tests/Production/ShuttleA/source_audit.py
python3 -B Tests/Production/StockVessels/original.py --suite shuttle-a --verify-inputs
python3 -B Tests/Production/NativeScene/prepare.py --delta-glider --shuttle-a \
  --data out/data --planets out/planets --destination out/shuttle-a-resources
python3 -B Tests/Production/CockpitUI/prepare_fonts.py --assets out/shuttle-a-resources
```

The four original profiles are now audited at producer `778b6c58`: 80 sessions,
4,800 presentations and 38,552 finalized all-vessel samples. Their exact archive
identities are pinned in `observations.lock.json`; there is no automatic refresh.
Stage and re-audit an existing cache with:

```sh
python3 -B Tests/Production/ShuttleA/frozen_original.py --offline \
  --cache out/phase6-shuttle-a-original-cache --output out/shuttle-a-original \
  --audit out/shuttle-a-original-audit.json
```

CI can obtain missing pinned Actions artifacts using its read-only
`GITHUB_TOKEN`. The helper strips authorization on redirects away from the API,
checks archive size and SHA-256 before extracting, and rejects unsafe paths.
An expired artifact is an error; it never selects a newer capture.

Capture success is not native qualification. Audit all four original profiles,
then compare the matching native captures with `StockVessels/compare.py --suite
shuttle-a`. Required-module failures must remain failures. The complete stock
corpus, hardware input/performance and lifetime gates remain separate.

The native workflow now captures all twenty sessions per build/CPU profile and
compares them against these exact original observations in four separate jobs.
`StockScenarios/ShuttleAPolicy.Test.py` checks missing modules, foreign factories,
generic fallbacks and unqualified class clones. It uses disposable resources
and must reject all eight variants before presentation without changing the
protected configurations. Use `--dependencies` for an owned Wayland compositor,
or run inside an already owned CI display such as `xvfb-run`.
