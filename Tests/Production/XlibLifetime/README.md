# Xlib resource and locale lifetime

The Intel X11 DG sanitizer checkpoint renders and deletes its context, then
fails leak checking with 46,197 bytes in 791 allocations. A loaded-library map
and renderer debug symbols place the allocation paths in libX11 resource/locale
initialization called by GLFW. No Orbiter allocation appears above that boundary.

A standalone executable loads and unloads Xlib without Orbiter, GLFW, OpenGL or
a display. Loading alone is clean. `XrmInitialize` retains 12,336 bytes in three
allocations; parsing and destroying a small resource database retains 27,334
bytes in 388 allocations in the C locale. Both the installed library and a
matching source build reproduce these failures. Their failed gates remain
recorded as failures.

## Isolated source candidate

`source.lock.json` pins Ubuntu's libX11 1.8.13 source archives, all nine matching
distribution patches and the local cleanup patch. `build_xlib.py` verifies the
inputs and installs only into a new owned prefix. It never replaces or activates
the system library. The prefix retains the license, source lock and patch, and
the build manifest records commands, compiler, feature checks and library hashes.
Its `built` status requires separate qualification.

The patch uses Xlib's existing shared-library destructor, before its thread-lock
teardown. Resource tables, permanent allocation arenas, locale descriptors,
converter and charset registries, input-method slots and compose caches retain
their normal loaded lifetime. Cleanup runs at the final dynamic-library owner
release. Locale descriptors use the existing concrete destruction method.
Only charset records constructed by Xlib acquire storage ownership; arbitrary
externally registered charsets remain borrowed. Replaced charset strings and
compose generations remain valid while existing consumers may reference them.
Both heap-backed and mapped compose caches are released on unload.

No simulator source, public Xlib record layout, exported symbol set, numerical
formula or accepted reference changes. The candidate requires Linux and Xlib's
default locale, thread-constructor and compose-cache features. Wider platform
and distribution acceptance remains open.

Build with a C toolchain, make, pkg-config, patch, X11/XCB development headers
and Python 3.12+ available:

```sh
python3 -B Tests/Production/XlibLifetime/build_xlib.py \
  --cache out/xlib-source-cache --output out/xlib-cleanup --sanitize
xvfb-run -a python3 -B Tests/Production/XlibLifetime/verify.py \
  --library out/xlib-cleanup/install/lib/libX11.so.6 \
  --output out/xlib-check --display
```

Run sanitizers outside a ptrace sandbox. No leak suppressions or library-retention
flags are used. The probe has no Xlib link dependency and checks `RTLD_NOLOAD`
after each final owner release. Twelve cases cover load-only control,
initialization, C and UTF-8 resource queries, hash-table/arena growth, a large
permanent string, four concurrent workers, overlapping owners, 24 complete
reloads, and real local input methods. Compose cases observe both live heap and
mapped paths, repeated invalidation with overlapping input methods, and a mapped
generation still borrowed after its backing file is replaced. The final process
map must contain no retained compose mapping.

The fixture owns its compose file/cache and adjusts only that file's mtime to
exercise Xlib's existing cache validity rule. Simulation clocks and references
are untouched. `--display` needs an unprivileged user and an owned X11 display;
omitting it runs the eight display-independent cases. Each output must be new.
`--offline` reuses only checksum-verified source archives.

The fully instrumented library is suitable for sanitizer executables. Python
drivers that themselves load Xlib through ctypes need a normal library build;
omit `--sanitize` for that prefix, then let the instrumented application detect
its allocations. Select a candidate only for the intended process:

```sh
env LD_LIBRARY_PATH="$PWD/out/xlib-cleanup-normal/install/lib" \
  ASAN_OPTIONS=detect_leaks=1:fast_unwind_on_malloc=0 LSAN_OPTIONS= \
  UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1 \
  python3 -B Tests/Production/DeltaGlider/systems.py \
  --build out/native-cockpit-asan --assets out/scene-resources \
  --data out/data --planets out/planets --output out/dg-systems-xlib
```

Native CI builds and checks the isolated instrumented library in every
Debug/Release automatic/SSE2 job. The application still uses the job's ordinary
system provider unless explicitly selected for a dedicated qualification.
