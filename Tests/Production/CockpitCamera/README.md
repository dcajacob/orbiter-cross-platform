# VC camera parity

This additional fixture compares both original Delta-gliders at forward and
turned `(0.8, -0.8)` and centered-downward `(0, -0.6)` VC angles. Each pose runs with scenario-loaded MFDs and
with both MFDs reopened through the public SDK. Every case runs twice for
60 fixed 0.25-second frames. It preserves the existing cockpit physical,
overlay and full-image budgets, including the 0.98 SSIM minimum.

The Windows observer links against the exact preserved `f7251942` application
SDK. `CockpitControls/prepare.py` verifies the original application, client and
shaders; the camera runner rechecks their bytes after building the new test
module. No application or client code is rebuilt for the original capture.
The native probe applies the same SDK commands before the first production
world update, calls both original session phases exactly once, and observes
the completed camera after `app.frame.end`. Initial physical state is observed
at tick 0; completed camera transforms cover ticks 1 through 60.

`InstrumentEvidence.h` assigns labels by pointer-valued surface handles and
does not observe their deletion. MFD reopening can reuse an address, so those
labels cannot identify persistent surfaces across runs. The raw drawing trace
is retained. `instrument-text-values.csv` projects out only `surface`; frame,
time, dimensions, coordinates, font, color, text and call order remain exact.
Independent left/right MFD captures and complete VC images still gate surface
contents and texture placement. Existing accepted reference files, producers,
comparators and thresholds are unchanged.

The paired comparison also projects the two original mesh display quads through
the observed original and native SDK camera transforms. Corresponding vertices
must agree within the existing one-pixel overlay bound. Each visible display's
framebuffer region must satisfy the same 0.98 SSIM minimum as the complete
frame. The centered-downward pose exposes both displays, so a local transparency
or texture-placement error cannot hide behind similarity elsewhere in the VC.

Capture natively:

```sh
xvfb-run -a env LIBGL_ALWAYS_SOFTWARE=1 GALLIUM_DRIVER=llvmpipe \
  python3 -B Tests/Production/CockpitCamera/run.py capture \
  --executable BUILD/orbiter-production --modules BUILD/NativeModules \
  --assets ASSETS --data DATA --planets PLANETS \
  --configuration Debug --math-profile automatic --output NEW_OUTPUT
```

On Windows, configure this folder with `ORBITER_TEST_RUNTIME` pointing to the
preserved runtime and build its SDK observer. Then use `capture --original`
with `--executable`, `--data`, `--planets`, `--mesa`, `--configuration`,
`--math-profile` and a fresh `--output`. The dedicated preserved-camera workflow
collects the four Debug/Release automatic/SSE2 reference matrices independently
of the longer native qualification.

Compare complete original/native matrices:

```sh
python3 -B Tests/Production/CockpitCamera/run.py compare \
  --original ORIGINAL_OUTPUT --native NATIVE_OUTPUT --output camera-comparison.json
```

Native repeatability alone does not establish original Windows image parity.
