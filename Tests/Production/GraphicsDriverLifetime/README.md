# Graphics driver lifetime reproduction

This standalone EGL test isolates the remaining native-client leak from Orbiter,
X11, GLFW, ImGui, vessel modules and the scene renderer. It creates one texture,
optionally generates mipmaps, deletes the texture, destroys the context,
terminates EGL, releases thread state, and unloads the graphics module. The
loader has no graphics-library dependency, so its `dlclose` exercises actual
driver unloading. It also checks anonymous executable mappings after unload.

```sh
cmake -S Tests/Production/GraphicsDriverLifetime -B out/driver-lifetime
cmake --build out/driver-lifetime
ctest --test-dir out/driver-lifetime --output-on-failure
```

Run outside a ptrace sandbox for LeakSanitizer. There is no display-server
requirement. Both tests require clean teardown and enable leak detection without
suppressions. A failing mipmap test is a real failed gate, not an expected-pass
exception.

On the laptop's Mesa 26.0.8-1ubuntu0.3 llvmpipe, the control without mipmaps is
clean. The mipmap case reproduces the simulator's two 56-byte leaks.
`/proc/self/maps` checks also show 10,485,760 bytes of anonymous executable
mapping remaining after library unload, compared with zero in the control.
Matching Ubuntu debug symbols identify `u_mmInit` lines 77 and 81, called from
`rtasm_exec_malloc` through the SSE vertex translator and the mipmap blitter.
The installed Gallium build ID is `b089ec2f62ded38e9327502246aa4ccfb7929b24`.

The [Mesa 26.0.8 source](https://archive.mesa3d.org/mesa-26.0.8.tar.xz),
`src/gallium/auxiliary/rtasm/rtasm_execmem.c`, allocates a process-global
`exec_heap` and a 10 MiB executable mapping. `rtasm_exec_free` returns individual
blocks to that heap, but this version never destroys the heap or unmaps the
region. The two heap bookkeeping objects become unreachable when the driver
unloads. Retaining the driver merely keeps the objects reachable and is not a
cleanup fix.

## Isolated cleanup candidate

`mesa-source.lock.json` pins the original and Ubuntu packaging archives plus
the local cleanup patch. `build_driver.py` verifies those hashes, applies the
Ubuntu patch queue and the cleanup patch, and installs only into a new output
directory. It never replaces the system driver or activates the candidate.
The prefix retains Mesa's license notice, source lock and patch; the build
manifest records commands, distribution patches and installed library hashes.
Its `built` status means compilation succeeded, not that qualification passed.

The patch releases the executable mapping and allocator bookkeeping when the
last generated function is freed. The existing allocator mutex protects this
transition. Live functions retain their mapping; a failed initial allocation
also releases any empty heap. It does not change generated instructions or
keep the driver loaded to hide leaks.

Build on Linux x86-64 with Python 3.12+, a C/C++ compiler, Meson 1.4+, Ninja,
pkg-config, patch, Bison/Flex, Python Mako/PyYAML, LLVM development files and the
Mesa X11/XCB, DRM, GLVND, zlib and zstd development dependencies available.
The verified local toolchain used GCC 15.2, Meson 1.10.1 and LLVM 21.1.8.
Dependencies must be provisioned separately; the builder does not install them.

```sh
python3 -B Tests/Production/GraphicsDriverLifetime/build_driver.py \
  --cache out/mesa-source-cache --output out/mesa-cleanup --jobs 4
python3 -B Tests/Production/GraphicsDriverLifetime/allocator_test.py \
  --mesa-build out/mesa-cleanup/build --output out/mesa-allocator-check
env LD_LIBRARY_PATH="$PWD/out/mesa-cleanup/install/lib/x86_64-linux-gnu" \
  __EGL_VENDOR_LIBRARY_FILENAMES="$PWD/out/mesa-cleanup/install/share/glvnd/egl_vendor.d/50_mesa.json" \
  LSAN_OPTIONS= UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1 \
  ctest --test-dir out/driver-lifetime --output-on-failure
```

The allocator test compiles Mesa's actual allocator sources with address and
undefined-behavior instrumentation. It executes overlapping generated functions,
frees one while calling another, verifies last-owner cleanup, checks an oversized
allocation failure, and runs 4,000 allocations on four threads. The unpatched
source fails the last-owner mapping check. The patched source passes without
sanitizer suppressions. The standalone EGL control and mipmap cases also pass
with the patched driver; the same source/toolchain without the patch reproduces
both the 112-byte leak and retained 10 MiB executable mapping.

The full Phase 6 ASan menu/Help flow also passes with this isolated driver,
including normal exit and a fresh process that reloads saved Options. Its
loaded-library map must identify the candidate Gallium library. The custom
Function test module preserves the inherited driver search path when prepending
the engine directory. Mouse clicks release the button before waiting for an
extra rendered frame, preventing a held Options button from repeating under
sanitizer overhead.

[`local-qualification.json`](local-qualification.json) records the fresh build's
source/driver hashes, failing baseline, passing allocator and EGL checks, and
513-frame application flow with a clean two-frame Options reload. Full local
logs are identified by path and SHA-256; the compact report retains the
standalone failure and success output.

This qualifies the tested software-driver candidate and application flow.
The installed system Mesa remains unpatched. Hardware drivers, distribution
rollout, other application lifetime sequences and the broader Phase 6 gates
remain separate work; Phase 5 launchers and frozen references are unchanged.
