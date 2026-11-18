# Linux x86-64 compatibility and source builds

The Ubuntu 24.04 package build uses the same application source revision as the
Ubuntu 26.04 preview (`f2fead9d259e93fd9fbfd3c432eda982030f2ec5`). It builds the
runtime and a matching SDK on Ubuntu 24.04. A separate Ubuntu 24.04 runner uses
only the resulting archives for the clean-install and SDK checks. The archive
audit checks glibc, libstdc++, C++ ABI symbol versions, and relative loader paths.
[Qualification workflow](../../.github/workflows/phase8-linux-ubuntu24.yml)

## Current supported preview

On a fresh Ubuntu 24.04 runner, the installed Launchpad decoded the 400 × 300
stock lunar-transfer screenshot, launched **DG Mk4 in orbit** from the installed
profile, and returned to the selected scenario. All 12 frames were presented and the
graphics context closed. The installer verified 1,192 stock files before and after
the flight. The SDK-built ShuttlePB presented 12 frames, completed its expected
callbacks and the runtime rejected a mismatched SDK module. GitHub's artifact
digests and the SHA-256 of each deliverable below were verified after download.
[Build and independent install](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/44246820332)

| Deliverable | SHA-256 |
| --- | --- |
| `Orbiter-linux-x86_64-ubuntu24.04.tar.gz` | `d870e397cdcc7e69e037e5599fe1e21ca6f749b45c24d6d0fbd190093ef468f4` |
| `Orbiter-SDK-linux-x86_64-ubuntu24.04.zip` | `2244e53d5b509050ea57c972631bdc2793473252a5e9a76f410ca1ebd0c77882` |
| `orbiter-stock-data-ubuntu24.04.pyz` | `552df640c6a8d2bdf605cfff2b7bcbcd5015ea9806f64d9ca0dc43015da571f9` |

## Earlier preview verification

The build and independent install checks passed on Ubuntu 24.04.5 LTS with
glibc 2.39. The install verified 1,192 stock data files, initialized Qt
Launchpad, and presented 12 frames of the unmodified Delta-glider flight.
The GCC 13.3.0 SDK rebuilt ShuttlePB outside the checkout. The installed
runtime loaded the add-on, read its mass through the SDK, destroyed it at
shutdown, and rejected the mismatched SDK module before initialization.
Both short flights used X11 software rendering and closed their contexts.
[Build and clean-install run](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/43681470045)

The ELF audit covered 26 binaries. The highest direct imports were
`GLIBC_2.38`, `GLIBCXX_3.4.32`, and `CXXABI_1.3.13`. The same audit rejected the
earlier 26.04 artifact at `GLIBC_2.43`. Distro support also depends on the
system Qt and graphics stack. The archive and receipt digests were checked
independently after download. They are retained under
`out/phase8-linux24-v1/run-43681470045/`.

| Deliverable | SHA-256 |
| --- | --- |
| `Orbiter-linux-x86_64-ubuntu24.04.tar.gz` | `e3716223f8a7a56d667b6156ae8d4d2c7eb836999c86319fab9bd182ca87a13f` |
| `Orbiter-SDK-linux-x86_64-ubuntu24.04.zip` | `995ba4c4ea7e0392ece99fb79a5f3770f744e996b73e84467e4057166bd8ce64` |
| `orbiter-stock-data-ubuntu24.04.pyz` | `e98538770f3f8c8ddff42818e8e7267bcffd37444538de49c9017e5745e76597` |

Use the listed installer for this runtime and the listed SDK for add-ons.
The full runs and Windows hands-on acceptance remain on hold.

## What a source build downloads

Install the compiler, build tools, Python 3.12 or later, Qt development files,
and Linux graphics development libraries through the distro first. On Ubuntu
24.04 the build uses these packages.

```sh
sudo apt-get install git cmake gcc g++ ninja-build python3 lsb-release qt6-base-dev \
  zlib1g-dev libgl-dev libglu1-mesa-dev libwayland-dev wayland-protocols \
  libxkbcommon-dev xorg-dev
```

CMake fetches the pinned Lua, ImGui, and ImPlot source inputs when needed.
The renderer's dependency helper downloads and verifies its SHA-256-locked
archives, including GLFW. The separate stock data installer handles the stock
resources and planetary archives.

Clone the integrated packaging branch with its history. The recipe builds the
pinned application revision in a detached worktree and writes the runtime and
matching SDK to `out/distribution/`.

```sh
git clone --branch qualification/phase8-install-review-v1 https://github.com/dcajacob/orbiter-cross-platform.git
cd orbiter-cross-platform
RUNNER_TEMP="$(mktemp -d)" bash Tests/Production/LinuxBaseline/build.sh
python3 -B Utils/StockDataInstaller/build.py --cache out/cache \
  --package-lock out/receipt/packages.json \
  --output out/distribution/orbiter-stock-data-ubuntu24.04.pyz
```

The installer builder fetches the two pinned stock-data archives if missing.
Use `--offline` with verified copies already in the selected cache. Transfer the
generated installer and runtime to a fresh location for use. The SDK is bound
to that exact runtime and toolchain.

## Supporting older distributions

Choose the oldest supported distro and build the runtime, third-party binaries,
and SDK against that baseline. In CI, check imported `GLIBC`, `GLIBCXX`, and
`CXXABI` symbol versions and run the short installation and SDK checks on each
supported distro. Verify the Qt and OpenGL dependencies, X11 and Wayland, and
the input stack on the systems included in the support claim.

Ubuntu 24.04 is the support floor. The [archived Ubuntu 22.04 experiment](Linux22Compatibility.md) bundled Qt 6.5.3 to
meet Launchpad's Qt 6.4 minimum. Ubuntu 22.04 ships Qt 6.2.4.
[Ubuntu 22.04 Qt package](https://packages.ubuntu.com/jammy/qt6-base-dev)

An AppImage can carry Qt and other selected dependencies. Build its runtime
and dependencies against the oldest target base system.
[AppImage build guidance](https://docs.appimage.org/reference/best-practices.html)
