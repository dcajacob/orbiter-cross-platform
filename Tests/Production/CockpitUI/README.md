# Original Windows selection and input references

This candidate gate runs the preserved original application, SDK and OpenGL
client from `production-windows-cockpit-v1`. The additional observation plugin
links the preserved SDK and reads the matching ImGui context. Target selection
and parameter entry start with actual glass MFD mouse buttons. Text and Enter
travel through the owned render-window procedure. The cancellation case opens
the original SDK input box and observes its cancellation callback.

Three cases cover Orbit target entry by name, Sync transit-list length and SDK
input cancellation. Each runs twice for 60 quarter-second steps. The gate checks
61 finalized vessel states, exact inputs and popup state, callback text, saved
MFD settings, stock instrument drawing and full rendered frames at 20 and 50.
Existing numerical, image and projected-geometry budgets apply. Font hashes are
recorded from the verified original data. The additional ImGui headers are pinned
by archive SHA256 and the SDK implementation supplies all ImGui functions.

These are candidate captures until Windows Debug, Release and cross-build
comparison pass and provenance is explicitly preserved. Native selection/input
integration depends on that acceptance. The capture workflow must become
manual-only when these references are frozen.
