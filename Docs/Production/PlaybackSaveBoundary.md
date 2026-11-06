# Playback and the exit-save boundary

The complete native stock-writer campaign at `2d6fa396`, collected by
`b6f9a1a0`, stopped on `2024 Edition/Space Shuttle to ISS.scn`.
Both repeats of the first two scenarios had passed in all four profiles.
The first compared third-scene run has exactly matching recorded all-vessel
physical state and camera, and image SSIM 1.0. Its complete save differs in
Leonardo's landed `POS`, `HEADING` and `ALT` records. This is a failed matrix.

The original Windows `Orbiter::CloseSession` ends playback before writing its
exit save. The native collector's explicit Save runs at finalized tick 960,
then `Runtime::Finish` ends playback later. `Vessel::FRecorder_EndPlayback`
resets the primary supervessel rotation; `SuperVessel::SetRotationMatrix` calls
`UpdateAttachments`, which calls the payload's `UpdatePassive` and refreshes
its cached surface parameters. `Vessel::WriteDefault` writes those cached
landed coordinates. This ordering provides a concrete explanation for a save
mismatch despite identical recorded flight state.

The [diagnostic record](PlaybackSaveBoundaryVerification.json) pins the actual
comparison and source identities. The repair aligns real EndPlayback/Save
ordering at the same finalized tick, retains every original scenario/reference
and budget, and compares complete save content as before. The original failed captures are
retained; they cannot be relabeled as aligned runs. Full38, class admission and
Phase 6 acceptance remain open.

The candidate collector now requests EndPlayback then Save at finalized tick
960, using the existing production playback method and unchanged save writer.
A versioned native boundary descriptor and actual ordered lifetime witnesses
make this explicit. Three controlled positives and fifteen damaged reader
controls cover the boundary checks. No extra physics tick, tolerance, saved
field exclusion or original-reference change is introduced. The rebuilt
stock-writer results below validate that boundary; the reload numerical gate
remains open.

Eight fresh stock-writer processes at `744b0729` now complete 7,680 presentations
with clean contexts and unsuppressed sanitizers, twice in all four profiles.
Independent re-reading and direct Windows comparisons pass complete saved
content, actual clocks, all-vessel physical state, camera and image SSIM 1.0.
The [writer verification](PlaybackSaveBoundaryWritersVerification.json) pins the
retained captures. This closes the observed stock-writer boundary discrepancy.

The exact-Windows-save reload campaign then stops on a distinct Debug/automatic
physical-state mismatch. Atlantis first exceeds the angular-velocity budget at
tick 242: `5.60984e-10 rad/s` against `1e-10`. Across that completed first run,
maximum angular-velocity error is `9.62782e-7 rad/s`, rotation `1.03210e-7 rad`
against `1e-8`, and velocity `3.61808e-5 m/s` against `1e-5`. Position stays within
its original budget. These are differing state values, not identical rows
misclassified by the comparison formula. Complete saved tokens still match;
serialization precision does not replace physical-state comparison. The
numerical cause remains open and no budget changes.

The first coordinator incorrectly expected a full-matrix status for a diagnostic
capture. Its next version omitted the independent reader's selected-scene
argument. Both wrapper failures remain retained. Completed Debug writers were
independently audited without relaunch; existing Release writer collectors were
adopted after their actual zero kernel exit status, then independently audited.
The corrected coordinator stopped the reload campaign on the real numerical
failure. Partial/cancelled observations earn no complete-matrix credit. The
full38 campaign has not been relaunched past this failure.
