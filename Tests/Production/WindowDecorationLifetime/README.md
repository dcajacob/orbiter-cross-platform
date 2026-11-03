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
