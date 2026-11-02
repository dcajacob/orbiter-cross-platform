# Intermediate production contact observations

This is a diagnostic build, not acceptance evidence or a replacement contact
model. Both frozen Windows references and their numerical budgets stay intact.
The ordinary production source, native preview and build directories are not
modified.

`prepare.py` checks the complete original `Vessel.cpp` hash, then inserts reads
of existing intermediate values into an isolated source copy under `out/`.
Removing precisely those insertions must recover every original calculation
byte. The generated source and observer hashes are recorded. No expression,
branch, assignment or integration stage is replaced.

The observation covers intermediate surface states, individual touchdown
vertices, normal/friction axes, per-vertex reactions, force limiting and the
resulting surface force/moment, gravity and final acceleration. It records the
first 41 simulation seconds, including the initial divergence, airborne flight
and controlled return touchdown. Object names, quaternions, cached forces and
gravity/proxy/communication scheduling values help distinguish changed inputs
from a changed calculation.
`contact-stages.jsonl` stores named doubles with 17 significant digits, in the
simulation's existing coordinate frames and SI units. `call` counts actual
`AddSurfaceForces` invocations, including calls that return before observation.

The [Windows workflow](../../../.github/workflows/production-contact-stages.yml)
rebuilds the original application/SDK at `391919027ac3e4a4d42f145373c788fc859c32cd`
with these reads, runs its existing tests, and recompiles the unchanged qualified
control drivers against the same build. Both the uncontrolled impact and
controlled landing must produce physical, input/callback, propellant and
animation CSVs byte-identical to the original frozen captures before
`windows.py` accepts their stage observations. A failed proof blocks analysis.

For Linux, prepare an isolated overlay and matching engine/renderer:

```sh
python3 -B Tests/Production/ContactStages/prepare.py \
  --source out/contact-stage-source --native-overlay
cmake -S out/contact-stage-source/Src/Orbiter/Production -B out/contact-stage-build \
  -DCMAKE_BUILD_TYPE=Debug -DBUILD_TESTING=OFF \
  -DORBITER_BUILD_NATIVE_VESSELS=ON -DORBITER_BUILD_NATIVE_CELESTIAL_MODULES=ON
cmake --build out/contact-stage-build --parallel 4
cmake -S OVP/OGLClient/Native -B out/contact-stage-renderer \
  -DCMAKE_BUILD_TYPE=Debug -DORBITER_ENGINE_BUILD="$PWD/out/contact-stage-build" \
  -DORBITER_RENDERER_DEPENDENCIES="$PWD/out/ogl-native-deps"
cmake --build out/contact-stage-renderer --parallel 4
python3 -B Tests/Production/ContactStages/native.py \
  --executable out/contact-stage-build/orbiter-production \
  --assets out/native-scene-resources --data out/native-celestial-data \
  --modules out/contact-stage-build/NativeModules --planets out/archive-data \
  --impact-reference out/native-ground-private-contact/pb_takeoff_landing-render-4 \
  --controlled-reference out/native-controlled-landing-complete/render-4 \
  --instrumentation out/contact-stage-source/contact-instrumentation.json \
  --output out/contact-stage-native
```

The reference arguments here identify the already failing, uninstrumented
native diagnostic runs. Their state hashes are checked explicitly. They never
replace the Windows acceptance reference. Both flights' complete state, control
and animation traces must remain byte-identical. Use the normal display or an
owned Xvfb display; software rendering requires the existing Mesa environment.
The output directory must be new.

After verifying the downloaded Windows artifact digest, compare only observations
whose physical-trace proofs passed:

```sh
python3 -B Tests/Production/ContactStages/compare.py \
  --windows PATH/out/contact-stages --native out/contact-stage-native \
  --output out/contact-stage-comparison.json
```

The report locates the first differing intermediate values and any subsequent
change in calculation structure. It has no acceptance override.
