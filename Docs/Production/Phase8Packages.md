# Phase 8 package and clean-install checks

These are Release preview archives. Each smoke check extracts a new copy of the
archive outside the source checkout, verifies the installed file manifest, starts
Qt Launchpad, and exercises the original **DG Mk4 in orbit** scenario. Stock and
planetary data are provisioned separately. These checks leave the full scenario
and mission suites and Windows hands-on acceptance deferred.

The [stock data installer](Phase8StockData.md) now provisions these four exact
archives and has passed a fresh-install stock flight on each platform.

## Linux x86-64

The later [Ubuntu 24.04 package, stock data installer, and matching SDK](Linux24Compatibility.md)
passed the same short installation and add-on checks on Ubuntu 24.04.
Ubuntu 24.04 is the oldest supported Ubuntu target. The earlier bundled-Qt
experiment is retained in the [archived 22.04 results](Linux22Compatibility.md).

The Ubuntu 26.04 archive passed on the laptop under an isolated X11 display. The
installed Qt Launchpad initialized with the system Qt 6 libraries. The installed
simulator and OpenGL module rendered and presented 12 frames and released the
graphics context. The working directory, simulator and data paths were all
outside the checkout. The package includes the pinned Lua library and the
matching OpenGL shaders. Stock data, planetary archives, and the temporary
cockpit test font were supplied outside the archive.
In a separate run of the extracted Qt Launchpad, clicking Launch opened the
stock flight, hid the Launchpad, and brought it back after Escape closed Orbiter.

- Application source `f2fead9d259e93fd9fbfd3c432eda982030f2ec5`
- Archive `out/phase8-packages-v1/Orbiter-linux-x86_64-ubuntu26.04-v2.tar.gz`
- SHA-256 `65e9f4b2c998eaa6f74c8552b0f25d4daa014f95dbe063a578f9440659b331d9`
- Receipt `out/phase8-packages-v1/linux-clean-install-external/clean-install.json`
- Qt Launchpad flow `out/phase8-packages-v1/linux-installed-launchpad-ui-v3/result.json`

## macOS Intel and Apple Silicon

Both native macOS 15 runners passed at `61baf018bbdc6a4e79e0a3d4b9d88baa40e62d92`.
The extracted Launchpad initialized Cocoa using the bundled Qt 6.8.3 libraries.
The stock flight rendered and presented 12 frames and released its graphics
context. The previews are ad-hoc signed and use the GLFW configuration that
allows Apple's software renderer on the hosted display. Local Mac hardware
acceptance remains open.
[GitHub run 43668062018](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/43668062018)

| Architecture | Archive | SHA-256 | GitHub artifact ID |
| --- | --- | --- | --- |
| Intel | `Orbiter-macos-x86_64.tar.gz` | `dba14169802041f88d6a49cc46023962a80f6b44e6ccf69825704966dce08ec1` | `14143203959` |
| Apple Silicon | `Orbiter-macos-arm64.tar.gz` | `6d942dd99fc523c7206360a214ee47f9e50ce284fed5550f98ede45fe701cf57` | `14142454682` |

The archives and audit receipts are retained under
`out/phase8-packages-v1/run-43668062018/`. The audit matched GitHub's artifact
digests, the archive digests, and the 108 per-file hashes for each architecture.

## Windows x64

The ZIP built from `9c18b6ff1011182deb1cc13abb8bb75bf57dcd2b` passed an
independent clean install on `windows-2025`. The test opened and closed the
installed Qt Launchpad with a sanitized DLL search path. The installed
simulator loaded the original Delta-glider, rendered and presented 48 frames
with OpenGL software rendering, and released the graphics context on exit.
The verifier used the exact build archive and its matching SDK.
[Build run](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/43668703790) ·
[Clean-install run](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/43669652170)

- Archive `out/phase8-packages-v1/run-43668703790/Orbiter-windows-x64.zip`
- SHA-256 `f9d184eb698ab0c7899b6c719cdd6c039c8e8414bb1f87f1efdb54bd071a64ef`
- GitHub artifact `14144100045`. The audit verified the artifact digest and all 2,379 installed file hashes.
- Receipt `out/phase8-packages-v1/run-43669652170/windows-clean-install-audited.json`

## Earlier attempts

[The first hosted run](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/43667639198)
retains the Windows locked-dependency failure and the Mac stock vessel compile
and link failures. The [first Windows retry](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/43667837379)
retains the rolling upstream stock download's checksum failure. The ZIP build
run retains the verifier's Windows environment lookup failure. The final
verification run corrected the lookup and reused the same ZIP. No release has
been published.
