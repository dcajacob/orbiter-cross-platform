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


The current-source replay now selects the private decoration plugin only for
Orbiter and records its actual mappings separately from the normal focus
client. The first globally exported selector caused that uninstrumented client
to fail ASan runtime-order initialization; the corrected explicit selector
passes actual software 1x and Intel PTL 2x canaries and rejects mismatched
plugin/build inputs before either application can launch. The simulator and
physics sources remain unchanged.

The broader replay then exposed an input-harness race in one software VC 2x
Options drag: input samples advanced before ImGui consumed the queued titlebar
press. A separately frozen helper now waits for completed GUI frames and actual
moved-window geometry while preserving every original pointer/camera check.
The same-package failed/fixed regression passes. Superseded coordinator outputs
and active flow results are preserved separately; a complete fresh 64-flow
DG/DG-S panel/VC, scale1/2, software/Intel matrix across all four build profiles
is running in the input-frame-sync checkout. Full current-source input and
Phase 6 acceptance remain open until that complete matrix and its independent
audit pass.

The current X11 typing replay exposed a second harness boundary race. Its
Debug automatic process accepted the target entry, but Ctrl-S was delivered
while the original popup still captured the keyboard: the save-key release
was observed at input tick 337, and the first uncaptured UI row followed at
tick 338. The failed process rendered 94 frames and deleted its context; it
produced no save. The driver now waits for flushed original UI observations
to show no popup and released mouse/keyboard capture before each save shortcut.
The same unchanged typing, parameter, cancellation, flight-key and save checks
pass in all four current profiles: four clean processes and 178 presentations.
The retained-source regression proves the helper preserves every original
input route and assertion, and checks all twelve actual corrected save
boundaries. [Scoped evidence](CaptureReleaseVerification.json) does not replace
the complete GUI, stock, platform or Phase 6 gates.
