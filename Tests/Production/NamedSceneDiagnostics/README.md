These diagnostics compare two observations from the complete DG orbit scene
with the exact previously captured Windows application, SDK and OpenGL client:
a second DeltaGlider's saved HUD mode during visual creation, and Orbit MFD
anomaly text when the original landed ShuttlePB becomes the focus.

Both derived cases preserve all eight original objects and the original epoch.
The first changes only the initial global HUD and the two DGliders' saved HUD
modes; the second changes only initial focus. The public SDK observer sets no
HUD, MFD, flight or camera state. Original default propagators remain enabled.
Each configuration/math profile runs both cases twice for 60 frames at 0.25 s,
with the existing 120 ms instrument refresh pacing. Complete rosters, finite
vessel states, real presentations, readbacks and deterministic repeats are
checked before emitting the diagnostic result.

The original runtime and client are downloaded from the already accepted
cockpit release and verified by their frozen archive and per-file hashes.
This workflow has no release, binary or evidence-archive upload step. Its
concise normal CI output can be retained locally. It does not refresh accepted
references or qualify unchanged named missions, full stock, image/numerical
parity, hardware performance or final Phase 6 acceptance.

The ordinary native application uses its fixed-step default for system time.
A bounded replay with only its header supplies the required pacing contract;
it contains no HUD, MFD, camera, keyboard or physics commands.
