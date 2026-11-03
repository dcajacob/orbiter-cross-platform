# Shuttle-A production port and original observations

The native cockpit build compiles the original Shuttle-A vessel, all panel
instruments, its Lua methods and the original parachute payload. Native module
factories use the checked SDK build identity. Shared drawing resources are
created for the first ship and released after the last ship is destroyed.
The native application still rejects Shuttle-A at its capability gate until
original Windows observations and native comparisons qualify it.

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

Capture success is not native qualification. Audit all four original profiles,
then compare the matching native captures with `StockVessels/compare.py --suite
shuttle-a`. Required-module failures must remain failures. The complete stock
corpus, hardware input/performance and lifetime gates remain separate.
