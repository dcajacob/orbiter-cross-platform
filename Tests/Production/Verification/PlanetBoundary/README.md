# Accepted Windows planet/base extraction

[Run 41297023065](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/41297023065)
at source `6b930c00269287c5a386baf70bb81e57b20b57bd` passed Debug and Release
application/SDK builds and actual Windows OpenGL client execution with Sol, ISS
and ShuttlePB. Numerical differences and projected landmark errors were zero;
both images matched the frozen original client with SSIM `1.0`.

The small ZIPs preserve original report bytes, build/toolchain metadata, loaded
Mesa DLL paths/hashes, invocation data, actual scene identities and asset hashes.
The provenance records original full GitHub artifact IDs, sizes and SHA256s,
plus filtered archive/member hashes. Full artifacts remain in CI; they are also
cached locally in `out/production-cache/planet-accepted-6b930`. Binaries and data
packages are excluded from these Git evidence archives.

```sh
python3 -B Tests/Production/Verification/PlanetBoundary/verify.py
```

This preserves Windows extraction evidence. It is **not** evidence of a native
Linux scene. The frozen original references and their tolerances are unchanged.
