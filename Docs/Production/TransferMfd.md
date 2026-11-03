# Transfer MFD lifetime and indicator verification

The admitted stock-corpus sweep exposed an uninitialized `dv_manip` read in
`Navigation/Lunar transfer/Lunar transfer 1.scn`. Fixing the initialization
exposed a second defect: a pointer to a branch-local rotation matrix was used
after that matrix's lifetime. Fixing its lifetime exposed a third defect:
a nonfinite predicted target direction reached an integer pixel conversion
and caused signed overflow. Each failed instrumented attempt is retained.

The repairs initialize the existing boolean, keep the same rotation matrix
alive through its consumer, and omit an indicator when either projected
coordinate is nonfinite. The orbital calculations and valid indicator
expressions are unchanged. No SDK layout changes were made. Exact source
restoration and four damaged-source controls verify the narrow delta against
`40a9b756598bf8486d373f469a86b6da31186d30`; the full 477-file source-conservation
check also passes.

Fresh, coherent engine/renderer builds at
`71a86988eaf25da1fc67778b0d1f1f7dab3aec75` were tested against the retained
pre-repair runtime. Both unchanged lunar-transfer scenarios retain all four
declared vessels. Each scenario ran in three fresh processes: the baseline
Release automatic build, repaired Release automatic build, and repaired Debug
automatic build instrumented with AddressSanitizer and UndefinedBehaviorSanitizer.
Leak detection remained enabled, with no suppressions.

All six processes exited with code zero, presented 60 frames each, and deleted
their graphics contexts normally. No sanitizer diagnostics occurred. The
baseline and repaired Release builds produced byte-identical physical state
CSV files for every vessel. The unmasked full-frame SSIM was
0.9988710379718454 for scene 1 and 1.0 for scene 2. Scene 1's frame changes where
the undefined indicator was drawn; scene 2's frame is byte-identical. These
comparisons are against the retained native baseline, not a new Windows parity
qualification.

The checkpointed runtime verifier is
`Tests/Production/Cockpit/transfer_runtime.py`; its qualified result is
`out/phase6-transfer-indicators-verification-v3/verification.json`. It records
actual process exits and checks that 531 source, verifier and runtime files
remain unchanged. Earlier interrupted attempts remain separate and do not
qualify as completed runs. Build commands, actual configurations, raw captures,
failed sanitizer baselines and evidence hashes are linked in the
[machine-readable record](TransferMfdVerification.json).

The verified local bundle is `out/phase6-transfer-mfd-evidence-v1.tar.gz`:
160,365,894 bytes, 1,402 members, SHA-256
`ba63294b0cc68b3a64c62063f19d04b96e26c105d96ac24807a718d14c74fa4f`.
Every archived file's hash was rechecked after packaging. Asset and font
collections are excluded; remote preservation remains open.

The historical admitted-corpus result remains 112 passed and 45 failed out of
157. These two targeted reruns resolve the Transfer MFD finding locally; they do
not replace that full-corpus result or complete Phase 6. The
[Lua explicit-exit finding](LuaProcessExit.md) is separately verified locally.
Current hosted checks, other stock dependencies and modules, final hardware
checks and remote preservation remain open. A physical
controller remains unavailable and unverified.
