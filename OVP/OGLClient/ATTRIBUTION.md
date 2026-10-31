# Selective OpenGL client adaptation

Renderer source and shaders originate in `TheGondos/orbiter`, commit
`ad96494482e6101afebf1c635e4e1f542623b51d`, under the original MIT notices.
The original per-file hashes are recorded in
`Tests/Production/renderer-donor.lock.json`. Only `OVP/OGLClient` source is
adapted. The fork's SDK, exported math types and application code are excluded.
These source files have been altered for the current SDK and Win32/WGL adapter;
they must not be represented as the unmodified historical renderer.

The separately built module implements current `GraphicsClient` callbacks.
`WindowsAdapter.cpp` owns Win32/WGL. GPU math and resource conversion stay in
this module; public Windows SDK layouts and virtual ordering remain unchanged.
This work is integration in progress until actual Windows application execution
and stock scene evidence pass. It is not a native Linux production application.

Dependencies are pinned by source-archive SHA256 in `dependencies.lock.json`:

* SOIL2: donor gitlink, public-domain declarations in source/README, plus the
  embedded stb notices. No icons or example programs are imported.
* NanoVG: donor gitlink, Mikko Mononen's zlib-style license; altered adaptation
  retains its original notice. Embedded fontstash/stb notices remain intact.
* libnsbmp: donor gitlink, MIT, Richard Wilson and Sean Fox.
* GLM: 1.0.1, MIT alternative selected; original `copying.txt` retained.
* FreeType: 2.13.3, FreeType License selected; original notices and `FTL.TXT`
  retained. Optional image/shaping dependencies are disabled explicitly.
* ImGui OpenGL backend: the exact current engine dependency commit, MIT. The
  engine's SDK configuration and same-build static library are used.
* zlib: same source revision as the production application, zlib license;
  linked privately/static into this renderer for planetary archive decoding.
* Generated GLAD loader: original notices in generated source/header; Khronos
  registry and loader attribution retained.
* Shader include helper: Tahar Meijs, MIT notice retained in `Shadinclude.hpp`.
* Sketchpad implementation: Matthew Reid attribution and MIT notice retained
  in `OGLPad.cpp/.h`, alongside Orbiter/Gondos contributions.

Downloaded source/license trees are build dependencies, not replacements for
stock vessel modules or planet data. The compiled client carries dependency
notices beside its shaders. Program/data licensing is recorded separately in
`Tests/Production/Licenses/INPUTS.md`.
