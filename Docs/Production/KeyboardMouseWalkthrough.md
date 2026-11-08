# Keyboard and mouse walkthrough

This walkthrough uses the separate Phase 6 development candidate and unchanged
stock scenarios. Allow about 20–30 minutes. A keyboard and mouse are sufficient.

Start with the full eight-vessel DG orbit scene, paused:

```sh
Tests/Production/Flight/run-cockpit-local.sh
```

The additional scene choices are `vc`, `docked`, and `takeoff`, for example:

```sh
Tests/Production/Flight/run-cockpit-local.sh vc
```

## Walkthrough order

1. Click inside the Orbiter window. Leave it paused while inspecting the view.
   Press F8 to cycle the glass cockpit, 2D panel and virtual cockpit. F1 switches
   between the cockpit and exterior. In the virtual cockpit, right-drag to look
   around and press Home to reset the view. The wheel changes the view's zoom.
2. In the 2D panel, use the arrow keys to pan the panel. Click the RCS mode
   selector and try the MFD buttons. Check that labels are readable, clicks land
   on the visible controls, and panel motion feels predictable.
3. Press Space to run. F selects rotational or linear RCS; Ctrl+F toggles it
   off/on. Briefly hold Alt+W, then release. Add Shift for reduced power.
   Check that jets stop on release. Rotation or drift can continue afterwards.
   Alt+K selects kill rotation. Press Space again to pause.
4. While running, hold an RCS direction and switch focus away from Orbiter.
   Release the keys before returning. Check that thrust stops and stays stopped
   when the window regains focus.
5. Press Ctrl+S to save, then F5 to reload. Check that the cockpit, instruments
   and vessel state return. Escape closes the walkthrough.
6. If those checks feel right, open `vc` for the landed DG-S cockpit. Try gear,
   nose cone and other cockpit controls. Use `docked` for the ISS scene or
   `takeoff` for a separate flight; each starts paused.

Tell me which step failed and what you saw. Readability, focus behavior, awkward
key combinations and mismatched click targets are all useful findings.

## Laptop bindings

| Action | Binding |
| --- | --- |
| Pause / resume | Space |
| Cockpit mode / cockpit–exterior | F8 / F1 |
| Look around / reset cockpit view | Right-drag / Home |
| Pan 2D panel | Arrow keys |
| RCS rotational–linear / off–on | F / Ctrl+F |
| Pitch or vertical translation | Alt+W / Alt+S |
| Yaw or lateral translation | Alt+A / Alt+D |
| Bank or backward–forward translation | Alt+Z / Alt+C |
| Reduced RCS power | Add Shift |
| Kill rotation | Alt+K |
| Increase / decrease main throttle | Alt+Page Up / Alt+Page Down |
| Cut main and retro thrust | Backspace |
| Increase / decrease hover throttle | Alt+Home / Alt+End |
| Aerodynamic controls | Alt+F |
| Faster / slower simulation | T / R |
| Save / reload | Ctrl+S / F5 |
| Options / close | F6 / Escape |

Bare vessel keys retain their original mechanism functions. For example, G
operates the gear and D operates the radiator. Manual thrust requires Alt.

Saves are separate for each scene under
`out/phase6-keyboard-mouse-walkthrough-v2/saves/`. Every launch gets its own
configuration and console log under `sessions/`; `latest-session.json` identifies
it. The launcher verifies Intel GPU rendering before continuing.

The first human walkthrough found laggy right-drag and a cockpit that retained
its old size after resizing. Its launcher had selected a software-only Mesa
provider. The corrected candidate uses the system Intel driver and refreshes the
native cockpit through the existing vessel layout callbacks. Live desktop checks
cover 960×540, 1280×720 and 1920×1080, actual resized RCS clicks, glass/2D/virtual
cockpits, preserved virtual-camera orientation, and exterior/cockpit re-entry.

This Release/automatic build is based on `f3e86add` plus the local native resize
correction, with matching modules and renderer.

The user confirmed the core keyboard walkthrough on 7 November 2026:

- Full-power and precision RCS register 100% and 10%, then stop firing on release.
- Kill rotation, pause/resume, ROT/LIN switching and RCS off/on work.
- Switching focus away stops thrust; returning does not restart it.
- Ctrl+S and F5 restore the saved cockpit view and MFD modes while paused.

These confirmations complete the core keyboard checkpoint. Other controls,
complete mission flows and full Phase 6 qualification remain separate.
