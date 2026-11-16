# Native paused attachment initialization v1

This native bootstrap revision keeps `assembly-contact-v3` physics unchanged. The original scenario reader skips independent orbit initialization for an attached child. A newly loaded paused native world therefore retained the child's default global pose until the first running physics step. A paused save could serialize a payload far from its parent.

After every module has restored its attachment points, the native bootstrap now updates child poses recursively from each unattached root. This happens before cockpit initialization, the initial observation, rendering and saving. It does not advance the clock or invoke a physics or module step. The Windows startup path is unchanged.

`source.py` permits only that exact bootstrap delta and this new version directory. It runs the original v3 guards in their retained source view; all original tests, readers, captures, source locks and tolerances retain their identities. `build_native.py` is a separately bound copy of the v3 builder, with the original compiler, sanitizer and package checks intact.

A new build is not acceptance. Actual paused startup, saved-state/F5, attachment lifecycle and affected full mission checks remain required for each candidate profile. Existing v3 captures remain attributed to their original runtime.

Run `python3 -B Tests/Production/NativePausedAttachments/source.py` to replay the guard chain, and `python3 -B Tests/Production/NativePausedAttachments/Version.Test.py` for the damaged-source rejection controls. Build the package with the separately versioned `build_native.py` and the same pinned dependency arguments as v3.

`Startup.Test.py --help` lists the explicit local package, data, provider and private compositor inputs. It exercises both original attached-payload scenes plus a free-vessel control on the real Intel renderer, with leak/undefined/address sanitizers enabled. It requires zero physics steps, 64 paused presentations, a complete original roster, exact parent/child transforms and a real paused save. An optional exact post-ascent save must also resave with no semantic differences. These bounded checks do not replace the full ascent, physical F5, four-profile lifecycle, original/current Windows or final acceptance gates.
