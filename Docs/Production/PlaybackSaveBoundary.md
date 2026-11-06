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
comparison and source identities. No boundary repair has earned runtime
qualification. The next check must align the real EndPlayback/Save ordering at
the same finalized tick, retain every original scenario/reference and budget,
and compare complete save content as before. The original failed captures are
retained; they cannot be relabeled as aligned runs. Full38, class admission and
Phase 6 acceptance remain open.

The candidate collector now requests EndPlayback then Save at finalized tick
960, using the existing production playback method and unchanged save writer.
A versioned native boundary descriptor and actual ordered lifetime witnesses
make this explicit. Three controlled positives and fifteen damaged reader
controls cover the boundary checks. No extra physics tick, tolerance, saved
field exclusion or original-reference change is introduced. Rebuilt runtime
comparison remains required before this candidate resolves the failure.
