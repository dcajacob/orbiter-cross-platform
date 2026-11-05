# Native Lua Terminal MFD

The native cockpit builds the original LuaMFD module as `Plugin/LuaMFD.so`.
Enable it in the explicit user configuration:

```ini
ACTIVE_MODULES
  LuaMFD
END_MODULES
```

The unchanged Atmospheric autopilot scenario selects `Terminal MFD` on the
left. While running, left Shift+I opens its input box; right Shift+I addresses
the right MFD. The stock NEW, DEL and page commands are retained. Terminal
commands run in the original interpreter and use the original DG/DG-S AAP.
For keyboard takeoff in this scenario, Alt+numeric-keypad Divide connects the
aerodynamic controls; the scenario starts with both aerodynamic and RCS input
disconnected. Numeric-keypad 2 raises the nose, and G retracts the landing gear.
The Terminal then accepts the stock `aap.alt(10e3)` altitude command.
Other application plugins still fail explicitly unless implemented by the
native host. Modules must match the engine's SDK and compiler ABI.

The module retains the stock drawing, commands, vessel/page repository and
callback order. Native interpreter workers use the existing execution handoff
and join before their Lua state or vessel is destroyed. Cockpit instances
are destroyed before the terminal module unregisters its mode. Terminal line
buffers are reclaimed, command copies are explicitly terminated, and failed
native construction releases the font and unpublished page. Vessel `V` uses
the existing canonical SDK userdata factory so the interpreter's validity
checks recognize it.

Run the source conservation check with:

```sh
python3 -B Tests/Production/NativeLuaMfd/source_audit.py
python3 -B Tests/Production/extraction_source.py
```

`native.py --help` lists the explicit package, asset, original data and local
provider inputs. It requires a completed source-bound ASan/UBSan build from
`RemainingVessels/build_native.py`. It runs the complete original eight-vessel
scene, types commands through the real Wayland input box, observes AAP engine
acceleration, deletes twenty busy terminal pages, saves all eight objects and
checks normal application/compositor teardown. It retains actual key edges,
MFD text/frame captures and source/runtime/resource hashes. Run
`audit_native.py --capture <directory> --output <fresh-report.json>` separately
on the closed result. Twenty pages are distinct from twenty application
sessions.

A complete-scene ground launch also exposed an uninitialized
`collision_speed_checked` flag in the original `VesselBase::SetDefaultState`.
The false initial value is now explicit; original ground-contact calculations,
propagators and update order remain covered by the source conservation checks.

This is an integration candidate. Local MSVC compilation, original/current
Windows full-scene startup observations and a development native interaction
run have passed. The native development run executed vessel-bound Lua, AAP
acceleration, twenty busy-page deletions and a full save with no sanitizer
findings. A separate constructor-failure run reclaimed the font and unpublished
page that the first failed startup leaked. Windows startup observations also retain a visible difference: the frozen
Terminal is blank below its title, whereas the canonical vessel-bound current
plugin prints the AAP startup/help lines. Observed flight-state rows and the
right Surface MFD are byte-identical. This is not an assertion of identical
Terminal output. Raw evidence stays local.

The complete unchanged eight-vessel Atmospheric autopilot tutorial has also
reached its conclusion in the manual Release/SSE2 sanitizer development build:
real keyboard takeoff and gear retraction, 10/20 km altitude and 300/600/250 m/s
speed commands, scramjet input, manual altitude override and recovery, low-speed
descent, help command and a full eight-vessel save. The application completed
11,694 presentations and closed without sanitizer findings. Its saved flight
also reopened with all eight objects for an airborne preview. These observations
do not establish original Windows numerical/image parity or all-profile
acceptance. Fresh immutable all-profile runs, full native/original comparisons
and complete session lifetimes remain required; this module does not by itself
qualify Phase 6.

Native Lua validity data now has one owner in the interpreter backend. Native
GNU builds avoid unique inline-data bindings so their module images can actually
unload; the original Windows declaration and object layout are retained.

The repaired local development runtime passes real `dlopen`/`dlclose` checks for
both Terminal and interpreter images, plus twenty complete eight-object
startup/teardown sessions in one process, with forty real presentations and no
sanitizer findings. These are lifecycle sessions, distinct from twenty complete
tutorials. Full all-profile and original-reference qualification remains open.
