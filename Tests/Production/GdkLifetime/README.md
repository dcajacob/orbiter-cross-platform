# GDK backend-string lifetime

Twenty instrumented application sessions initially complete 1,200 presentations,
all context deletions and identical state traces, then report 152 bytes in 19
allocations from `gdk_set_allowed_backends`. The unchanged GTK decoration plugin
calls that setter for each initialization. GDK 3.24.52 duplicates the supplied
string and overwrites its previous pointer without releasing the copy.

The candidate records ownership of setter copies separately from the borrowed
default `"*"`. It duplicates the new input before freeing the previous owned
copy, so input aliasing is safe and a borrowed default is never freed. Backend
selection, the environment-variable policy, public headers and all other
source bytes are unchanged. The application continues to use GTK decorations.
The [public API documentation](https://docs.gtk.org/gdk3/func.set_allowed_backends.html)
describes the caller's input ownership and when backend selection takes effect.

## Build and verify

The qualified platform is Ubuntu 26.04 x86-64, GTK 3.24.52-0ubuntu1, GCC 15.2,
GLib 2.88 and Meson 1.10. Install no candidate into the system. Supply the normal
GTK development dependencies and usable GLib resource, enum, marshal and D-Bus
code generators through the build environment. A private development prefix
must expose correct generator locations in its pkg-config metadata.

```sh
python3 -B Tests/Production/GdkLifetime/build.py \
  --cache out/gtk-source --output out/gdk-baseline --baseline --sanitizers
python3 -B Tests/Production/GdkLifetime/build.py \
  --cache out/gtk-source --output out/gdk-candidate --sanitizers
python3 -B Tests/Production/GdkLifetime/qualify.py \
  --baseline out/gdk-baseline --candidate out/gdk-candidate \
  --output out/gdk-qualification
```

Use `--meson` for a private build tool. The builder verifies the original and
Ubuntu source archives, applies the distribution patch queue, checks exact
before/after source hashes and compiles all three installed GDK backends:
Broadway, Wayland and X11. It keeps `/usr`, `/etc` and `/var` as the compiled
runtime paths. It never runs installation rules: only GDK libraries and notices
are copied into the fresh private output. `built` is separate from qualified.

Run the sanitizer controls outside a ptrace sandbox. One setter call is clean
with every library. Twenty calls reproduce 152 bytes/19 allocations with the
installed system and rebuilt baseline, and become clean with the candidate.
The diagnostic borrowed-default case opens an unavailable backend before the
setter calls to exercise the existing literal-default path. It is an ownership
control, not a recommended application initialization order. The independent
lost-allocation control must still report 73 bytes/one allocation with the
candidate; baseline and system report that object plus the 19 overwritten
backend strings. All GDK symbol names and types must match both the baseline
and installed library. No sanitizer annotations or suppressions are used.

Application qualification requires explicit application-only library selection,
actual loaded-library identities and clean process exits. System installations,
accepted Windows references and numerical/image budgets remain unchanged.
The earlier private-prefix prototype and the reproducible builder's system
runtime paths are recorded separately; a fresh binary needs its own scoped
qualification evidence.
