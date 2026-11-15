# Orbiter Phase 8 preview SDK

Each SDK targets the exact runtime archive named in `sdk.json`. Extract the SDK
and runtime separately. For an installation created by the stock data installer,
use its `runtime/` directory. Build the supplied example with CMake 3.24 or later
and a single-configuration Release build.

```sh
cmake -S /path/to/sdk/example -B /path/to/build -G Ninja \
  -DCMAKE_BUILD_TYPE=Release -DOrbiterSDK_DIR=/path/to/sdk/cmake \
  -DOrbiterRuntime_ROOT=/path/to/install/runtime
cmake --build /path/to/build
```

Use GCC 15.2.0 with the Ubuntu 26.04 libstdc++ ABI for Linux. Both Mac SDKs use
the Apple clang and libc++ from Xcode 16.4 used by their runtime. On Windows
use an x64 Developer Command Prompt with MSVC 19.51.36260.0 (toolset
14.51.36231) and Windows SDK 10.0.26100.0.

For your add-on, use `find_package(OrbiterSDK CONFIG REQUIRED)`, declare a CMake
`MODULE` target, and call `orbiter_sdk_vessel(your_target)`. Copy its binary to
`Modules/` on Windows or `NativeModules/Vessel/` on Linux and macOS. Add the
vessel configuration under `Config/Vessels/` on Windows. The Windows example
defines the new vessel class `Phase8SdkProbe`. The Linux and macOS example
rebuilds the stock `ShuttlePB`. Use a disposable installation for that example
because it replaces the stock module. Both examples record lifecycle events
in the simulator's working directory.

The Windows kit contains the classic SDK shipped in the matching Windows
preview. The Linux and macOS kits support source-built native vessel add-ons
with this preview's compiler and bootstrap ABI. The existing stock-class
admission guard still applies on Linux and macOS. Use a matching SDK for each
subsequent runtime.
