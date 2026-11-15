# Orbiter stock data installer

Use Python 3.12 or later and one of the four Phase 8 preview archives. Run
the standalone `orbiter-stock-data.pyz` with a new destination directory. The
preview archive and the two stock data downloads are checked by size and
SHA-256 where the pinned manifests specify them.

```sh
python3 orbiter-stock-data.pyz "Orbiter Preview" --package Orbiter-linux-x86_64-ubuntu26.04-v2.tar.gz
```

On macOS use the `arm64` or `x86_64` archive. On Windows run
`py -3.12 orbiter-stock-data.pyz "Orbiter Preview" --package Orbiter-windows-x64.zip`,
or use your installed Python executable if you use a later version.

- Linux starts with `Launch Orbiter.sh`. macOS starts with `Launch Orbiter.command`.
  Both use the included Launchpad profile and keep configuration and saves in
  `user/`. The package retains its platform requirements and signing status.
- On Windows open `runtime/orbiter-launchpad.exe` or `runtime/Orbiter.exe`. The
  Windows application keeps its usual configuration and scenario layout under
  `runtime/`.
- The first install downloads approximately 4.1 GB of pinned archives. Plan for
  about 10 GB of free space for the cache, the installation and temporary files.
  The default cache directory is `~/.cache/orbiter-stock`. Use `--cache DIR` to
  choose another directory and `--offline` to use verified local copies of
  `production-stock-data-v1.zip` and `Orbiter2016.zip`. Rerun the same command to
  resume an incomplete download. If the server does not support Range, the
  installer safely restarts that download. A complete archive with the wrong
  hash must be moved out of the cache before retrying.
- Run `python3 orbiter-stock-data.pyz "Orbiter Preview" --verify-only` to check the
  installed data without going online. The installer leaves an installation
  receipt and retains the original data notices in `notices/`.
- The 2016 planetary archive's publisher terms are in
  `notices/planets/Doc/Orbiter.pdf`. The installation supplies Cousine for the
  manuscript font. Separately distributed audio assets and optional textures
  are outside this installer.

To build the standalone installer from a source checkout, run
`python3 -B Utils/StockDataInstaller/build.py --cache DIR --output orbiter-stock-data.pyz`.
The builder uses the existing original-resource stagers and locks.
