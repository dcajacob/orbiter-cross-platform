# Dragonfly Windows cockpit repair candidate

The preserved remaining-stock v2 campaign failed in all four profiles. Four
Dragonfly cockpit scenes reported invalid bitmap/surface dimensions and later
OpenGL failures, while the external-view Molniya scene completed after delivery
of the byte-exact original mesh at its installed path. All original failed ZIPs,
decoded members and producer sources remain in
`out/phase6-remaining-stock-original-failed-v2`.

The Windows OpenGL client inherited the SDK's null `clbkGetSurfaceDC` and empty
release callback. Dragonfly uses those callbacks to create compatible panel
bitmaps and draw its original instruments. The client now supplies a real 32-bit
top-down DIB selected into a memory DC, reads the actual texture into that DIB,
and uploads GDI's completed RGB drawing when the DC is released. A lease holds a
real surface reference and owns its DC/bitmap. Outstanding leases are reclaimed
before client textures and the render context. Pixel-transfer state, buffer and
texture bindings, and the calling thread's WGL context are restored.

The original ADI also left its own bitmap WGL context current after
initialization, assumed that context remained current during later drawing, and
cleared the caller's context during destruction. Its original rendering and
attitude calculations now run inside explicit context ownership. Initialization
and cleanup restore the caller; painting acquires its own context and restores
the caller before SDK GDI/blit calls. Its owned target also handles construction
failure and unused-context destruction. `Tests/Production/Dragonfly/source_audit.py` checks all
23 original source/header/resource files against `f7251942`, allowing only those
declared context bindings. No public SDK layout or physical calculation changes.

`Tests/Production/WindowsSurfaceDC` runs in the actual production Windows app.
Each of two fresh scene processes exercises 100 odd-sized surface round trips,
18,200 checked pixels, 50 rounds with a separate compatibility WGL context, real GPU
blits, nondefault pixel-transfer state, compatible-bitmap format/dimensions, and
GDI object counts. It requires the complete ordinary Sol/ISS/ShuttlePB scene's
physical traces and full framebuffer to remain byte-identical, as well as the
existing frozen numerical comparison. The Windows client workflow builds and
runs this control in Debug and Release and retains its raw evidence.

The first actual runtime control at `06553328` could not establish the requested
bitmap WGL pixel format under Mesa. Its exact Debug ZIP is retained in
`out/phase6-surface-dc-failure-v3`, SHA-256
`0e283eef00496e06dcbc464551e27e702d0ec2339caaebebb60b1c56b09517a7`.
The ADI now owns a noninteractive compatibility window/context and a real
160-by-160 offscreen color framebuffer. It retains the original request for zero
depth/stencil bits, runs the unchanged original GL commands, then reads the
result into a real bottom-up 32-bit GDI bitmap. It restores the caller before the
original SDK bitmap copy. Geometry, lighting, projection, attitude calculations
and SDK blit arguments remain exact in the source audit. The public SDK stays
unchanged.

The surface control now exercises a real separate window compatibility context
and the actual ADI target implementation. Two additional readbacks check
compatibility display lists, color, vertical orientation and creation/drawing/
destruction context restoration. The same GDI object-count and byte-identical
ordinary-scene gates remain required. These replacements await fresh execution.

These are implementation candidates awaiting their hosted controls. Actual
Dragonfly complete-scene capture, four-profile state/image comparisons, controls,
save/reload, native rendering and lifetime qualification remain open. The
preserved v2 reference is not refreshed or reclassified by these changes.
