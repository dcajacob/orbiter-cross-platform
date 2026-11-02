# Accepted original Windows selection and input reference v1

Run 41541262748 at ccb9215e passed all three cases twice in Debug and Release.
The original f7251942 application/SDK and 68400a7d OpenGL client came from the
hash-verified parent cockpit archives. The additional SDK observer recorded
actual window messages, popup state, finalized vessel states and saved MFD
settings. Orbit selected ISS by name, Sync stored LISTLEN 3, and cancellation
called the original SDK callback with the entered text.

Debug/Release numerical and projected-geometry errors are zero. All captured
full-frame and MFD images compare at SSIM 1.0. Inputs, popup observations,
callbacks, instrument text and HUD atlas updates are exact. Every artifact and
reference file is pinned in provenance.json. The capture workflow is manual-only.

These references cover the three declared workflows. Further menu navigation,
focus transitions and native UI execution require additional verification.
