# Wayland input and windowing lifetime

All sixteen local instrumented input flows now pass: DG and DG-S, 2D panel and
virtual cockpit, at 1x and 2x, on Intel PTL and llvmpipe. They complete 14,808
presentations, original RCS picks, keyboard/focus release, camera input and held
button shutdown, with context deletion and clean process exits. C/C++ sources
compiled by the engine and renderer builds are instrumented, as is the isolated
Fontconfig candidate. Prebuilt CSPICE and system libraries retain their builds.
ASan/UBSan/LSan remain enabled without suppressions.

The 273 KB Fontconfig report has now been isolated as an ownership-tracing
false positive. A reachable pattern owns its heap element table through a
relative offset, which a conservative checker cannot follow. The three-site
candidate stores an actual pointer for heap patterns while keeping serialized
patterns' existing offsets and constant-reference marker. The cache remains
owned by Pango; the application does not clear it or change GTK decorations.
The retained-owner control becomes clean, while both libraries still report
all 82 allocations and 2,992 bytes when the owner is deliberately lost.

The original, candidate and installed system library produce identical selected
metadata for all 535 system fonts and all fourteen matching queries. The dynamic
symbol names/types match. The original PCF fixture produces byte-identical
binary caches across two baseline rebuilds and the candidate. Each library
reads the other's cache without changing either bytes or modification times.
All fourteen configured upstream tests also pass with the first candidate.
The [pinned builder and public-API controls](../../Tests/Production/FontConfigLifetime/README.md)
reproduce the ownership and compatibility checks in fresh private prefixes.

The previous Mesa cleanup build supported X11 only. Selecting it for Wayland
failed to obtain an EGL display; that retained failed run is not qualification.
The builder now has an explicit `--wayland` option that adds Wayland alongside
X11, using the same locked source and executable-heap cleanup. The eight software
input flows use this new build. The eight hardware flows use the installed Intel
driver. All flows explicitly select the Fontconfig candidate. The input runner
records ELF hashes and actual mapped paths and verifies binary stability. Its
independent focus client and compositor keep their own normal runtimes.

The failed EGL creation also exposed an application resource leak: renderer
teardown returned immediately when no window existed, leaving a successful
`glfwInit` unbalanced. The adapter now tracks initialization and terminates GLFW
on that path. The normal window destruction sequence is conserved. Invalid
widths 0 and 20,000 and the incompatible EGL provider reproduce sanitizer
findings with the old renderer; the fixed renderer rejects the same requests
with the same messages and exit code 1, without sanitizer findings.
`Tests/Production/WaylandInput/initialization.py` retains the regression.

Fresh renderer builds use copies of the unchanged verified engine/module
binaries and their exact matching SDK header. Earlier runtime directories and
failed captures are retained. Original Windows references and every numerical,
pixel and timing budget remain unchanged.

[WindowingLifetimeVerification.json](WindowingLifetimeVerification.json) records
source and runtime identities, scoped results and local evidence. System
libraries are unchanged. The local evidence bundle contains 4,465 members;
every payload and symlink was verified after archiving. Its digest and size
are recorded in the verification JSON. It retains failed prototypes and the
system Mesa control, which still reports 112 bytes in two lost allocations.
Remote publication remains open. Current-source hosted qualification, remaining stock
modules and failure-path crashes, physical controllers and remote evidence
preservation remain open. Phase 6 is in progress.

A later `c10db131` native control completed 60 presentations and graphics
teardown, then reported 14,085 bytes/123 allocations in GTK's title-bar icon
path. That failed run remains retained in
`out/phase6-atlantis-tank-lifetime-v7/detached-below`. The original libdecor
0.2.5 GTK plugin releases the icon pixbuf but omits the caller-owned icon-info
release. Its private one-release candidate is pinned to the exact 52 upstream
and distribution source files. A real 120-update Wayland control observes each
baseline icon's reference count grow from 1 to 121 and every candidate return
at 1. The independent 73-byte lost-object control still fails precisely under
both libraries, with all sanitizers enabled. Source, controls and raw evidence
are described in the
[decoration ownership fixture](../../Tests/Production/WindowDecorationLifetime/README.md).
Broader current-source application/input qualification with this dependency
candidate is pending; the preceding sixteen-flow result retains its recorded
source/runtime scope.
