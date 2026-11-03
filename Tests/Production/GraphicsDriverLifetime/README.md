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
cleanup fix. A driver cleanup fix and full simulator verification remain open.
