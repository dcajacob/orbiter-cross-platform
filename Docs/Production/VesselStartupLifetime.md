# Vessel startup and docking-record lifetime

The 25 signal-terminated scenes in the preserved complete stock sweep now
reject their missing dependencies with exit code 1, no sanitizer findings,
zero presentations and normal context deletion. Every original scenario byte
and declared ship is retained. Both legacy and extended SDK creation also
reject an unavailable class without leaking its name allocation. These are
error-handling results; the scenes remain failed stock cases until their
required modules are available and qualified.

The original crash occurs during partial-session destruction. Scenario parsing
temporarily encodes dock partners' names in the mate field. `PostCreation`
resolves those tokens only after all vessels load. A later missing class throws
before that phase, and destruction tries to undock an unresolved token with no
superstructure. `ClearDockDefinitions` now checks that its mate is a live world
vessel before invoking the original undocking path. Successfully resolved
partners retain their existing processing order.

Three constructor branches now release the class-name allocation before
reporting a missing configuration. The first repaired runtime then exposes a
second ownership omission: `Vessel::Read` releases its temporary fuel and
thruster arrays but leaves the parsed docking-record array allocated. The
records have already been copied into port state by `SetStateEx`; the temporary
array is now released there too. The earlier sanitizer capture retains the
32-byte, two-allocation report.

These five cleanup sites are the only changed bytes of `Vessel.cpp`. The
conservation audit restores exactly those spans before comparing every other
byte with the preceding implementation. Missing cleanup, a removed mate check
and an unrelated control calculation are rejected by negative controls. The
complete 444-file source audit passes. No class fields, SDK layouts, numerical
formulas, scenario inputs or accepted reference budgets change.

Fresh Debug instrumented and Release automatic engine/renderer builds preserve
all preceding runtimes. C and C++ sources compiled by the instrumented engine
and renderer use ASan/UBSan; LeakSanitizer remains enabled without suppressions.
The independently qualified private Fontconfig and Wayland-capable Mesa
candidates permit unsuppressed lifetime checks; system libraries are unchanged.
Prebuilt CSPICE retains its build.

All fourteen Release automatic station captures still pass the audited Windows
state, capability, port, camera and full-frame image budgets. Eight instrumented
single-session flights cover docking/undocking, approach, creation/deletion and
attachments at two render frequencies. Their states and lifetime callbacks
match the immutable Windows references, remain independent of render frequency
and exit without sanitizer findings.

The broader repeated-session check remains failed. All twenty sessions complete
sixty presentations, unregister their visuals, delete their contexts and produce
identical flight states. Process exit then reports 152 bytes in 19 allocations
from `g_strdup` / `gdk_set_allowed_backends` through the installed GTK decoration
plugin. That retained report requires owning-source analysis. It is not counted
as a clean repeated-session sanitizer pass, and no suppression or decoration
policy change is introduced.

[VesselStartupLifetimeVerification.json](VesselStartupLifetimeVerification.json)
records source and runtime identities, rejected scenarios, successful-path
checks and evidence. [The rejection driver](../../Tests/Production/StockScenarios/README.md#startup-rejection-regressions)
keeps stock acceptance separate from clean dependency rejection. The complete
157-scene instrumented sweep is also being repeated. Missing vessel modules,
current hosted qualification, physical controllers and remote evidence
preservation still prevent Phase 6 acceptance.
