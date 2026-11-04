# Complete remaining stock-module observations

This fixture measures every physical object in all 38 unchanged locked stock
scenes that declare an unimplemented native vessel or payload class. It does not
admit any new native class or complete Phase 6. Native implementation and its
matched profile/state/camera/image/interaction gates remain separate work.

The selection includes 30 Atlantis scenes, its boosters and external tank,
Carina, Leonardo and station payloads, Dragonfly, HST, LDEF, SolarSail and
Quadcopter. All 19 initial declared class configurations and all 36 existing
recording files are pinned to original source
`f725194209634f7fd5d1d44d426cfa9b5e303e37`. All 38 scenarios retain their original
names and bytes. Original Windows launch arguments use Windows-native separators.
Each requested playback must be active at its first observed tick. Existing
optional recording streams remain present or absent exactly as shipped.

The unchanged application, client and public SDK are staged by the established
preserved-runtime loader; only the passive SDK observer is rebuilt. Every scene
runs twice in native Windows Debug/Release automatic/SSE2 profiles: 304 total
processes, 60 fixed quarter-second frames each. This is a 15-second observation
of each complete scene, not an entire mission or tutorial. The original state,
clock, camera and full-frame budgets remain unchanged.

The observer records all actual vessels at every finalized tick, including
vessels generated during initialization or subsequent staging. Declared objects
must be present initially. Every actual public docking port, parent and child
attachment, individual thruster, propellant resource, mesh slot and playback flag
is recorded. Shared external tank handles resolve to the owning actual vessel and
resource index. Deleted mesh slots remain explicit; the renderer must identify
every present physics mesh at the captured frame, with matching object classes.
No focus-only or simplified scene can satisfy this protocol.

The capture protects all preserved application/SDK/client bytes, raw staged
configuration/mesh inputs, actual observer/DLL identities and producer sources.
`Gate.Test.py` rejects twelve damaged copies of a real complete launch stack.
`audit_original.py` binds every decoded member to all four exact downloaded ZIPs,
rechecks independently retained SDK/client packages, actual MSVC source/config/CRT,
loaded modules, repeats and paired state/camera/full-frame budgets. Extra per-
thruster/tank/attachment/mesh numeric differences are reported as calibration;
these new fields do not create or relax an existing numerical tolerance or
establish native parity.

Measurements and independent audit are pending. No observations lock is created
or refreshed automatically. Use fresh outputs and never rebuild accepted
applications, SDK packages or native packages to obtain a different reference.

```sh
python3 -B Tests/Production/RemainingStock/original.py --verify-inputs
```
