# Assembly contact physics v3

This version retains every v2 change and adds separate initial/trial state buffers
around the dynamic `SuperVessel` integration. Supervessels are outside the general
body update list, so they otherwise retain aliased `s0`/`s1` pointers. A rejected
collision step then overwrites the initial state needed by its retry.

The local unchanged-method and whole-update controls reproduced the complete
original HST failure byte for byte. An observer recorded retries changing the
starting angular state. Traps located angular overflow in the original Euler
equation. The isolated state-buffer prototype completed HST launch and all four
earlier failing scenarios using the original 60 frames, quarter-second clock,
full vessel rosters, sanitizers and independent numerical reader.

These are diagnostic results, not qualification of a new application. Fresh
source-bound native builds, full Linux checks and independent audits are required.
Windows and macOS work is deferred under the user's Linux-first instruction.
Hardware performance and physical-controller acceptance remain pending.

`source.py` permits only the exact incremental production change and the separately
versioned builder. All v1/v2 guards, capture identities, comparison tolerances,
failure records and test bodies remain unchanged. The original v2 guard runs in a
real checkout of its immutable source, and in turn replays the original guards on
their original source. Old captures never become evidence for v3.
