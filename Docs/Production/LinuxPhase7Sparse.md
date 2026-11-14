# Linux Phase 7 sparse results

The Linux sparse milestone passed on November 14, 2026 on the laptop's
Release/SSE2 candidate `41f8a7314d350cc198ef07a7daab879c4d02d55f`. The checks
used ASan, UBSan and LeakSanitizer with leak detection enabled and no
suppressions. The original scenarios and acceptance tolerances remain in force.

| Check | Result |
| --- | --- |
| Wayland settings and joystick | Options survived restart. The wizard round trip verified mappings, idle throttle, neutral RCS and reconnect. The physical VelocityOne red-pad press activated Kill Rotation and reduced angular speed from 19.7°/s to less than 0.001°/s with the throttle at idle. |
| Qt Launchpad and in-flight editor | Landed and orbiting scenario copies survived launch, save and reload. The paused editor added, moved and removed vessels with the resulting state preserved on reload. |
| Native XRSound | Delta-glider main-engine and RCS audio passed, including pause, resume and reload. |
| Wayland regression | Five short stock flights, 11 selected unit checks and both frozen source guards passed. |
| X11 Options | The original stock-menu test passed save, reload and normal graphics teardown using private patched Mesa llvmpipe under Xvfb. It passed again with a profile produced by the generator. |
| X11 stock startup | 11 selected original scenarios each completed 60 presentations and all 61 state snapshots with their full vessel rosters and clean graphics cleanup. A separate run checked the optional Earth 2006 atmosphere. |

The X11 stock selection covered the Kennedy Space Center tour, the Space Shuttle
to ISS launch stack, Atlantis ISS Resupply, HST Launch, Dragonfly PoweredUp,
Solar sail, Quadcopter at KSC, Shuttle-A Drop, Atmospheric autopilot, Olympus
spaceport on Mars and Lunar eclipse 2004. The checks observed load and close
events for all 11 vessel module types, with actual mappings for SPICE, Earth
J71G, Mars 2006, Lua Inline, Lua Interpreter and Lua MFD. The additional Earth
2006 run changed the atmosphere selection in a private copy of the assets.

## X11 driver fix

The installed Mesa 26.0.8 llvmpipe reproduced two 56-byte losses and retained a
10 MiB executable mapping when a standalone mipmap test unloaded the driver.
The patched build released the mapping and exited cleanly in the same test.
The original Orbiter settings run also passed with the patched GLX and Gallium
libraries confirmed in the simulator's process map. The [Launchpad profile
generator](../../Utils/Launchpad/README.md#x11-software-rendering) selects that
private driver for X11 software rendering. The system Mesa package still
contains the bug. The regular hardware profile continues to use its normal
driver.

## Retained evidence

These reports are local to the qualification checkout under
`out/qt-launchpad/phase7-linux-sparse/`. SHA-256 digests identify the retained
reports and preserve their original candidate identity.

| Report | SHA-256 |
| --- | --- |
| `integrated-stS0PE/summary.json` | `7d92b04c14ecabe8593638ecbcd99c08f57877cda0e5bc3d45240b165a31252c` |
| `physical-red-pad-0KGCqU/result.json` | `7f80ad39ff27c6a596934e74fd7cb54bdb77bfb3338bcbd8cae983186c2f237f` |
| `x11-closeout-j5ZxSk/summary.json` | `189bb0299d3e9342101a7da4cf5cffa9bd12ed0a8a079e166790bffe3eb3c07c` |
| `x11-closeout-j5ZxSk/stock-and-modules.json` | `8f358775d7db54a3ce97375bcee20412b854b9b6f70e2ec4dd5f7b2717a8de2a` |
| `alternate-atmosphere-C0F3lE/stock-and-modules.json` | `b4295245b57128a5246e7f0d89149af773825523df23a330bab43a3660bd371e` |
| `profile-commit-O0Fuyf/flight/menu-verification.json` | `f1afe2f00dd54d88fd3fcf3142d459a5e85641b3ee609b5dc792cdffca664446` |

The 157-case stock suite and complete mission runs are deferred by request.
Formal cross-platform and release qualification remain open.
