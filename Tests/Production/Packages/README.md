# Orbiter Phase 8 package preview

Extract the archive into a fresh writable directory. The program runs without
the source checkout. Provision the original stock resources, SPICE data and
standard planetary archives separately. The Phase 8 smoke uses the existing
locked data provisioners on a disposable test copy.

On Linux the runtime uses the target distribution's Qt 6 Widgets, OpenGL and
desktop libraries. Start the Qt Launchpad with `bin/orbiter-launchpad`. On
macOS, the Qt Launchpad app carries its Qt libraries. Use Setup in Launchpad to
select a native simulator profile. Copy the packaged shaders into the asset
root under `Modules/OGLClient` as part of provisioning. The profile points to the extracted
`orbiter-production`, `NativeModules`, and separately provisioned asset, data,
and planet directories. Use writable copies for the configuration and saves.

The Windows x64 archive installs by extraction. Start `orbiter-launchpad.exe`
in the extracted Orbiter directory or use the original `Orbiter.exe`.

These are qualification previews. Graphics checks run on hosted software
renderers or an isolated local Linux display.
