# Shared production celestial world

The original `PlanetarySystem` loader, object ownership, module dispatch, and
update/finalization loops now build in the shared core. Required vessel and
composite-vessel operations are explicit services. The Windows adapter calls
the actual existing `Vessel`/`SuperVessel` methods in their original order.

The native component observer constructs the actual Sol `PlanetarySystem`,
including 41 celestial bodies, 40 planets/moons and 39 bases, using actual native
SPICE/atmosphere modules and verified stock assets. It advances 6,000 one-second
steps and records all 41 finalized body states every tenth step. It does not
construct native vessels, a camera or a renderer; requests for unsupported
vessel operations fail explicitly in this test host.

The verifier reads the existing frozen production Windows reference without
altering it. It compares all 601 Sun/Earth/Moon samples (1,803 states) using the
unchanged position, velocity, orientation, epoch and mass budgets. The remaining
38 bodies have finite-state/rotation/repeat checks here; their original SPICE
callbacks retain the separate frozen 41-body module parity gate. CI additionally
compares all 41 body traces between the four Windows/Linux Debug/Release builds.
No comparison claims vessel, camera, scene or full-session parity.

```sh
cmake --build out/production-boundary --parallel 2
python3 -B Tests/Production/World/verify.py \
  --executable out/production-boundary/production_native_world_observer \
  --modules out/production-boundary/NativeModules \
  --data out/native-celestial-data --planets out/archive-data \
  --output out/native-world-verification-debug --configuration Debug
```

Two independent runs must produce identical numerical CSV bytes. A deliberately
missing required Earth module then exercises partial-world cleanup after other
real bodies have loaded. It must fail explicitly without a replacement module
or generic vessel. Run under ASan/UBSan/LSan to verify both successful teardown
and that failure path. Original system construction now cleans a partially
created world before rethrowing a resource/module exception.

Local Linux Debug, Release and strict sanitizer runs observed zero Sun/Earth/Moon
position, velocity and epoch error against Windows, with orientation difference
about `3.14e-16 rad`. These are local component results, distinct from hosted
Windows/Linux acceptance. Base enumeration ordering, the native vessel SDK,
actual vessel modules, full session/camera lifetime and graphics integration
remain work for the native application.
