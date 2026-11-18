# Archived Ubuntu 22.04 x86-64 experiment

The supported Ubuntu baseline is 24.04. This record preserves the earlier 22.04 experiment and its artifact identities.

The Ubuntu 22.04 package uses the same Orbiter application source as the
24.04 preview (`f2fead9d259e93fd9fbfd3c432eda982030f2ec5`). The build runner
uses Ubuntu 22.04.5 LTS, glibc 2.35, and GCC 11.4. Launchpad uses bundled
Qt 6.5.3 shared libraries and platform plugins. The system supplies EGL,
OpenGL, and the X11 and Wayland client libraries.
[Qualification workflow](https://github.com/dcajacob/orbiter-cross-platform/blob/ececd1e1f6de56cabe72feefaadb5b086e0672ff/.github/workflows/phase8-linux-ubuntu22.yml)

The stock data installer needs Python 3.12 or later. The SDK is tied to the
exact runtime archive and native build. The archived SDK check used the matching Ubuntu 22.04 SDK
and GCC toolchain. The workflow lists
the system packages used for the build and for a clean installation.

## Download checksums

| Deliverable | SHA-256 |
| --- | --- |
| `Orbiter-SDK-linux-x86_64-ubuntu22.04.zip` | `0504ae22cdbfce58ed3829f3b129d69b7f08dcd84dfb7f074873b7defb418a21` |
| `Orbiter-linux-x86_64-ubuntu22.04.tar.gz` | `374e876dbd7335a2dec2b9cd84bff11720d7ea487709f0317fb30609a6030142` |
| `orbiter-stock-data-ubuntu22.04.pyz` | `28940a3e9ce0c6932b803257cf25320a7ad0a9c92d14b5d2cbbd56105c98176a` |

## Verification result

A separate Ubuntu 22.04.5 runner installed the package outside the source
checkout and verified 1,192 stock data files. Launchpad loaded the bundled Qt
XCB plugin. The stock Delta-glider and the SDK-built ShuttlePB each rendered
and presented 12 frames, then closed their graphics contexts. The SDK check
verified the module callbacks and rejected a mismatched SDK module before
initialization. Both checks used X11 with software OpenGL.
[Build and clean-install run](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/43693556470)

The ELF audit covered 63 binaries and found maximum symbol versions of
`GLIBC_2.35`, `GLIBCXX_3.4.30`, and `CXXABI_1.3.13`. The downloaded
GitHub archives, file manifests, and exact SDK-to-runtime binding were
independently verified. The packages and test receipts are retained under
`out/phase8-linux22-v1/run-43693556470/`.

The short checks cover X11 with software rendering. Wayland, physical GPUs,
and distros older than Ubuntu 22.04 remain unverified. Full runs and Windows
hands-on acceptance remain on hold.
