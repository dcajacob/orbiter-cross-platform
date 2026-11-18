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

## Verification

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
