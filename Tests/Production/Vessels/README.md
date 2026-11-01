# Native production vessel components

This component host runs the original `PlanetarySystem`, `Vessel`, SDK vessel
wrappers, SPICE, J71G and source-built ShuttlePB. ISS uses its actual stock generic
configuration. It is not a graphical application, camera, input or cockpit gate.
There is no fallback for a required missing native vessel module.

```sh
cmake -S Src/Orbiter/Production -B out/native-vessels -DCMAKE_BUILD_TYPE=Debug \
  -DORBITER_BUILD_NATIVE_CELESTIAL_MODULES=ON -DORBITER_BUILD_NATIVE_VESSELS=ON
cmake --build out/native-vessels -j4
python3 -B Tests/Production/Vessels/verify.py \
  --executable out/native-vessels/production_native_vessel_observer \
  --modules out/native-vessels/NativeModules --data out/native-celestial-data \
  --planets out/archive-data --configuration Debug --output out/native-vessel-verification
```

Data preparation uses the existing immutable celestial and planetary locks.
All RCS/autopilot/callback-fixture numerical states match the correctly staged,
frozen Windows behavior profile, with the original budgets. These are numerical
state checks, not acceptance of callback event ordering. Both 6,000-step native
orbit/control runs must repeat identically and remain finite; their matching
long-duration Windows comparison remains outstanding. The early orbit reference
used a different atmosphere profile; see its [record](../Reference/README.md).

Native modules must be rebuilt from source with this exact SDK/build/toolchain.
Library lifetime extends through all vessel resource teardown, including static
module-owned animation transforms. Public Windows SDK types, exports and virtual
ordering are retained. Native cockpit, panel, HUD and physical input services
remain explicitly unavailable in this headless host.

Sanitizers found and corrected two original cleanup bugs in shared code: scalar
`delete` on an animation pointer array, and missing frees of owned constant
exhaust coordinates/directions in bulk exhaust cleanup. No numerical formulas,
force tables, propagation order, frozen evidence or budgets were changed.
