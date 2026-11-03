# Fontconfig heap ownership tracing

The isolated GTK Wayland window initially reports Fontconfig allocations at
exit. Fontconfig 2.17.1 stores a heap pattern's element-table address as a
relative offset. A conservative leak checker cannot follow that offset from
the still-reachable owning pattern. The retained-owner control reproduces
2,968 reported bytes in 81 allocations while the owner remains in a live
global variable. Destroying that owner releases all allocations.

The three-site candidate stores the actual table pointer for heap patterns.
Serialized patterns keep their existing relative offsets, identified by the
existing constant-reference marker. Structure fields, sizes, cache version,
serialization writes, allocation/free calls, reference counts and font matching
expressions are unchanged. This corrects tracing of existing ownership; it
does not release, retain or ignore additional objects, change the decoration
backend, or add sanitizer annotations or suppressions.

Both original and candidate libraries still report the same deliberately lost
owner: 2,992 bytes in all 82 allocations. The candidate also passes the retained
and released controls. This distinction is required before treating the GTK
report as an ownership-encoding false positive.

## Reproduce

Use native Linux x86-64, Python 3.12+, a C compiler, Meson, Ninja, gperf, binutils,
and FreeType/Expat development headers. The qualified host is Ubuntu 26.04 with
Fontconfig 2.17.1-3ubuntu1, GCC 15.2 and Meson 1.10.1. Other distributions and
architectures require their own qualification.

```sh
python3 -B Tests/Production/FontConfigLifetime/build.py \
  --cache out/fontconfig-source --output out/fontconfig-baseline \
  --baseline --sanitizers
python3 -B Tests/Production/FontConfigLifetime/build.py \
  --cache out/fontconfig-source --output out/fontconfig-candidate --sanitizers
python3 -B Tests/Production/FontConfigLifetime/qualify.py \
  --baseline out/fontconfig-baseline --candidate out/fontconfig-candidate \
  --output out/fontconfig-qualification
```

Pass `--meson` when using a private build tool. Run the instrumented programs
outside a LeakSanitizer ptrace sandbox. The builder verifies pinned original
and Ubuntu archives, applies the distribution patch queue, checks both source
inputs and effective outputs, and copies libraries and notices into a fresh
private prefix. It keeps the actual system font configuration paths and never
runs installation rules that write to those paths. A `built` manifest reports
compilation; qualification is separate.

The qualifier checks real ownership and lost-allocation controls, seventeen
font fields for every installed font, fourteen matching queries, dynamic
symbol names/types, exact serialized cache bytes for the original 4x6 PCF
fixture, and both cache readers without rewriting their inputs. Results from
the installed system library must also match. The first candidate additionally
passes all fourteen configured upstream tests with ASan/UBSan/LSan enabled.
No accepted Orbiter reference or image/numerical budget is refreshed.

## Application scope

The native Wayland input runner accepts repeated `--library-directory` options
for explicit application-only selection. It records ELF hashes, verifies that
each directory supplied a mapped library and checks that the libraries remain
unchanged. The independent focus client and compositor retain their own normal
runtimes. An instrumented candidate is used with the instrumented application;
the system Fontconfig installation is unchanged.

The minimal unchanged GTK decoration flow passes without a Pango cache reset.
The earlier private-font-map prototype remains failed experimental evidence;
it was not adopted. The separate Mesa allocator cleanup still addresses its
real lost allocations. Local application captures and remaining Phase 6 scope
are recorded in [WindowingLifetime.md](../../../Docs/Production/WindowingLifetime.md).
