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
the caller before SDK GDI/blit calls. An ADI that never initialized a context
skips context destruction. `Tests/Production/Dragonfly/source_audit.py` checks all
23 original source/header/resource files against `f7251942`, allowing only those
declared context bindings. No public SDK layout or physical calculation changes.

`Tests/Production/WindowsSurfaceDC` runs in the actual production Windows app.
Each of two fresh scene processes exercises 100 odd-sized surface round trips,
18,200 checked pixels, 50 rounds with a separate bitmap WGL context, real GPU
blits, nondefault pixel-transfer state, compatible-bitmap format/dimensions, and
GDI object counts. It requires the complete ordinary Sol/ISS/ShuttlePB scene's
physical traces and full framebuffer to remain byte-identical, as well as the
existing frozen numerical comparison. The Windows client workflow builds and
runs this control in Debug and Release and retains its raw evidence.

These are implementation candidates awaiting their hosted controls. Actual
Dragonfly complete-scene capture, four-profile state/image comparisons, controls,
save/reload, native rendering and lifetime qualification remain open. The
preserved v2 reference is not refreshed or reclassified by these changes.
