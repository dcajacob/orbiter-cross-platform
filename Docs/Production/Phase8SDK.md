# Phase 8 preview SDKs

Each SDK binds to one retained Phase 8 runtime archive and its Release toolchain.
The SDK includes a CMake package and a vessel example. CMake checks the runtime
file hashes before linking. The Linux and Mac packages use their native runtime
libraries and check the exact compiler, standard-library ABI, and architecture.
They recover the generated build identity from the sealed runtime and corroborate
it against its Delta-glider, OpenGL renderer, and SPICE module. The Windows SDK
preserves the headers, import libraries, and other SDK files from the sealed
Windows archive.
[Developer instructions](../../Utils/PackageSDK/README.md)

## Verification scope

The Linux SDK built the ShuttlePB sample from the extracted kit outside the
checkout. The installed preview loaded it, configured it, read back its empty
mass through the SDK, and destroyed it at session close. The unmodified stock
Delta-glider flight presented 12 frames. The independent mismatch control was
rejected before its initialization callback. Runtime and stock source inputs
retain their original identities.

The native preview's stock-class admission guard remains in force. The new
example class from the initial Linux trial passed the bootstrap loader and was
rejected by the existing class check. The final native kits use a rebuild of
the admitted stock ShuttlePB, with lifecycle observations added to its factory.
The Windows kit uses a new vessel class through the classic SDK.

Both Mac examples passed the same 12-frame stock flight and mismatch check.
The new Windows class appeared in the in-flight vessel roster during the
48-frame check. Normal simulator shutdown called the vessel destruction
callback and returned to the classic Launchpad. The first Windows run used
the fast-exit option and did not call that callback. The second run used the
same SDK bytes and the original runtime with the normal shutdown path.
[Mac and first Windows run](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/43679686604) ·
[Windows normal-shutdown run](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/43680088183)

The exact tested SDK archives and `SHA256SUMS` are retained in
`out/phase8-sdk-v1/final/`.

| Kit | SHA-256 |
| --- | --- |
| `Orbiter-SDK-linux-x86_64.zip` | `d21677ff102368520e8362e0235f61cb5a96b01aae4c6d64d0f98e15a6a53673` |
| `Orbiter-SDK-windows-x64.zip` | `02119174fe643c3c4a5c8284616d4d1d57aefc1ac9f3387537b2fe50e3052d9a` |
| `Orbiter-SDK-macos-x86_64.zip` | `c2873f94a4f4c98e1f291b60f3837221503b663c9ab0a8effbcffb3ad27fbe0d` |
| `Orbiter-SDK-macos-arm64.zip` | `6e37fdcd2a6c2531d805fa0f031a0eb2ab6fbb7094980a53299c731fbe3adbd1` |

Full runs and Windows hands-on remain deferred. The hosted checks exercised
software rendering. These results cover the documented build-bound SDKs and
their vessel examples.
