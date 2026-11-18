# Phase 8 stock data installer

`orbiter-stock-data.pyz` creates a fresh installation from a checksum-locked
Phase 8 preview archive. It works without a source checkout and uses Python
3.12 or later. The installer includes the extra native scenario and vessel
assets. The original stock data and standard planetary archives are fetched
separately and checked against the existing locks. Interrupted downloads can
resume, and `--offline` consumes the same verified archives from a local cache.
[Installer usage and cache layout](../../Utils/StockDataInstaller/README.md)

The installer preserves all 157 locked stock scenarios and 28 planetary archive
files. Native installations include a Launchpad profile and keep configuration
and saves under `user/`. Windows keeps the compatible portable layout under
`runtime/`. Cousine supplies the manuscript font without requiring the
separately licensed Architext font. The original data notices are installed
under `notices/`.

## Getting a rebuilt preview

The refreshed Windows and Mac archives use the eight-character source suffix
`72b1741e` in the installer lock. From the packaging checkout, fetch the
archive with its verified install name, then use the standalone installer. The
following example uses Windows x64. For macOS use
`Orbiter-macos-arm64-72b1741e.tar.gz` or `Orbiter-macos-x86_64-72b1741e.tar.gz`.

```sh
python -B Tests/Production/StockInstaller/fetch_package.py Orbiter-windows-x64-72b1741e.zip packages
python orbiter-stock-data.pyz "Orbiter Preview" --package packages/Orbiter-windows-x64-72b1741e.zip
```

The fetch helper uses the GitHub CLI to verify the source commit and both the
outer and inner archive digests. Previously retained packages keep their own
names and hashes. The Ubuntu 24.04 installer and its matching runtime and SDK
are distributed together. [Ubuntu 24.04 instructions](Linux24Compatibility.md)

## Refreshed installer verification

The installer passed at commit `df04fc301b86e6af6f4caa99a5090075e82bef68`
with SHA-256 `3e3dd67c16ffadb52dbbe7aa21eeb4cf0dc4ddb5e9ba8993c270c0657282c1db`.
Windows verified 497 managed data files. Each Mac verified 1,192. The rebuilt
runtime hashes and sources are recorded in the [package lock](../../Utils/StockDataInstaller/packages.json).
Both Macs decoded the stock 400 × 300 JPEG through the installed Launchpad,
launched the original Delta-glider, presented 12 frames, and restored the
selected scenario on return. Ubuntu 26.04 passed the same Launchpad check
with its retained runtime and the refreshed installer.

Windows used its installed configuration and presented 48 flight frames plus
the default exit-preview frame. The saved scenario referenced `CurrentState_img`,
and the renderer closed its context. The original package check still
requires exactly 48 presentations with exit capture disabled. The audit
verified the GitHub artifact digests and matched each result to the runtime
and installer hashes. The test-driver failure records are retained in the
earlier run. [Passing installer checks](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/44253340712) ·
[Earlier attempt](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/44249889595)

## Earlier preview verification

The installer was built from `91db1aa0cc381c441bfd2ed20a1818e8d65dc868` and has
SHA-256 `380062a5372c625208e3e3a8ca08e48f7f97cf65c05349876aeefcd781ec9f7a`.
The locally built and hosted installers match byte-for-byte. The retained
copy is `out/phase8-stock-data-v1/run-43670613897/orbiter-stock-data.pyz`.
[Hosted qualification](https://github.com/dcajacob/orbiter-cross-platform/actions/runs/43670613897)

Linux x64 (Ubuntu 26.04) passed an offline install into a fresh external
directory. It verified 1,192 installed files before and after the original
Delta-glider flight, which rendered and presented 12 frames and released
its graphics context. Tests also verified interrupted HTTP resume, fallback
when a server returns the full response, bad range rejection, offline checksum
enforcement, detection of a damaged installed file, and preservation of an
existing destination.

| Package | Installed data files verified | Stock flight |
| --- | ---: | --- |
| Linux x64 (Ubuntu 26.04) | 1,192 | 12 frames presented, clean graphics teardown |
| Windows x64 | 497 | 48 frames presented, clean graphics teardown |
| macOS Intel | 1,192 | 12 frames presented, clean graphics teardown |
| macOS Apple Silicon | 1,192 | 12 frames presented, clean graphics teardown |

The Windows and Mac runs fetched the pinned data on standard hosted runners,
started the installed Qt Launchpad, and flew the original Delta-glider from
each fresh installation. Each job verified the managed data both before and
after flight. The independent audit verified the GitHub artifact digests,
installer SHA-256, package identity and individual result records. The Mac
results use the hosted software renderer, and the Windows test uses the
original finite smoke probe. Full runs and Windows hands-on remain deferred.
