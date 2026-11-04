# Isolated Wayland decoration lifetime

This test creates a real window with the renderer's checksum-pinned GLFW 3.5.1,
clears and swaps 120 frames, destroys the window and terminates GLFW. C and C++
use ASan/UBSan/LSan without suppressions. There is no Orbiter engine, cockpit,
font renderer, texture loading or mipmap generation.

```sh
cmake -S Tests/Production/WindowDecorationLifetime \
  -B out/window-decoration-lifetime -G Ninja -DCMAKE_BUILD_TYPE=Debug \
  -DORBITER_GLFW_ARCHIVE="$PWD/out/ogl-native-deps/glfw.tar.gz"
cmake --build out/window-decoration-lifetime
ctest --test-dir out/window-decoration-lifetime --output-on-failure
```

Run under an owned disposable Wayland compositor, inheriting its
`XDG_RUNTIME_DIR` and `WAYLAND_DISPLAY`, outside a LeakSanitizer ptrace sandbox.
The existing verified fixture is `Tests/Production/WaylandInput/compositor.py`.
Both tests require clean teardown; the known failing baseline is not marked
`WILL_FAIL` or converted into a passing lifetime gate.

`prefer` selects GLFW's default preference for libdecor. On the tested Ubuntu
26.04 host it loads libdecor's GTK plugin and reproduces Fontconfig allocations
reported through GTK/Pango at exit. `disable` selects GLFW's builtin decoration
path for this diagnostic only. It completes the same 120 swaps and teardown
with exit code zero and no sanitizer report. The loaded-library maps prove
the GTK plugin is present only in the first case. This isolates the decoration
dependency path; it does not establish the exact missing cleanup inside it.

The production renderer's decoration preference and system libraries are
unchanged. The full instrumented simulator's exit remains a failed gate.
`out/phase6-window-decoration-capture-final/` retains the two process logs,
loaded maps and a hash manifest. The integrated application evidence is linked
from [RendererDefinedBehavior.md](../../../Docs/Production/RendererDefinedBehavior.md).

Subsequent [Fontconfig ownership controls](../FontConfigLifetime/README.md) show
why the retained owner's encoded table is misreported and verify a tracing
compatible representation. The original and candidate still report identical
genuinely lost allocations. The unchanged GTK window is clean with that
explicitly selected candidate, without changing its decoration preference or
resetting the shared Pango map. Historical system-library reports remain here.

## GTK icon-info ownership candidate

A later current-source tank deletion control completed graphics teardown, then
reported 14,085 leaked bytes in 123 allocations. Its three direct GObject
allocations originate in `gtk_icon_theme_lookup_icon_for_scale` through
libdecor's three title-bar buttons. The raw failed run is retained in
`out/phase6-atlantis-tank-lifetime-v7/detached-below`. libdecor 0.2.5 releases the
loaded icon pixbuf but omits the returned `GtkIconInfo`. GTK assigns ownership of
that return to the caller in its
[public API contract](https://docs.gtk.org/gtk3/method.IconTheme.lookup_icon_for_scale.html).
The private patch adds that one release after drawing.

`libdecor-icon-source.lock.json` pins the official upstream and Debian source
archives from the distribution descriptor. Both Ubuntu and Debian supplied the
same descriptor bytes; all 52 extracted source/package files match the retained
baseline exactly. `build_icon_owner.py` verifies that complete tree, applies only
the declared release, checks the plugin's actual exports and sanitizer linkage,
and builds into a new private directory. It performs no system installation.

```sh
python3 -B Tests/Production/WindowDecorationLifetime/build_icon_owner.py \
  --cache out/phase6-libdecor-source-cache-v1 \
  --output out/libdecor-icon-candidate \
  --meson out/phase6-mesa-build/deps/usr/bin/meson \
  --meson-pythonpath out/phase6-mesa-build/deps/usr/lib/python3/dist-packages \
  --development-prefix out/phase6-decoration-build-deps/root/usr --sanitizers
```

Use `--baseline` in a separate fresh output for the unmodified source.
The source-bound prototypes in `out/phase6-libdecor-icon-owner-build-v1` have
completed two baseline and two candidate real native sessions. All four exit
cleanly, retain 60 presentations and context deletion, and have byte-identical
complete state/control/animation traces and full frames. Raw evidence is in
`out/phase6-libdecor-icon-application-v1`. This validates unchanged application
behavior in that paired sample. Leak elimination, independent lost-allocation
controls, repeated real-window ownership and broad dependency qualification
remain open because the fresh baselines also exited cleanly. The normal
application's dependency selection and historical failed gate remain unchanged.

The optional `ORBITER_ICON_OWNER_PROBE=ON` CMake target now provides a read-only
GTK return observer and a real GLFW title-update window. The observer forwards
every original argument and return, reads the live public GObject reference
count, and keeps addresses only as text. It retains no strong object references
that could taint leak scanning. The window performs 120 actual title updates
and swaps with normal GTK decorations. Its separate `lost` mode loses a 73-byte
allocation on a joined worker thread.

`out/phase6-libdecor-icon-controls-v1` records 363 actual button-icon lookups in
each of four processes. Each baseline icon's reference sequence is exactly
1 through 121; each candidate sequence contains 121 samples of 1. Both libraries
still detect precisely 73 bytes/one allocation in the lost-object mode. The
independent byte/hash/sequence audit is
`out/phase6-libdecor-icon-controls-audit-v1.json`. This demonstrates the missing
release even when the default theme's reachable cache prevents an exit-time
leak report. The reproducible baseline and candidate builders also complete in
fresh outputs, with the exact descriptor export and requested sanitizer linkage.
Application regression with the pinned candidate and wider lifetime coverage
remain required before changing normal runtime dependency selection.

The pinned candidate now passes the three actual native tank controls at
`c10db131`: 180 presentations, three clean context deletions and sanitizer exits,
508 guarded source/dependency inputs and 1,102 unchanged assets. Each process
verifies the candidate's actual loaded path and hash. Complete state, controls,
animations, thrust and frames remain byte-identical to their retained baselines,
including the process that previously ended with the GTK leak. Evidence is in
`out/phase6-atlantis-tank-lifetime-v8`; its independent plugin/state/frame audit is
`out/phase6-libdecor-icon-native-regression-v1.json`. The full input/backend/
scale/hardware matrix and delivery integration retain their separate gates.
