# Fixed-clock original UI reference

The original Windows application, SDK, renderer and selection/input action
schedule come from the preserved cockpit baseline. A test-only ImGui
NewFramePre hook sets each GUI frame's delta to the same quarter-second step as
the physics fixture. Popup fades and caret blinking therefore advance by a
known amount. The original Select and InputBox implementations draw the dialogs.

The accepted captures and comparison are recorded in [Reference](Reference/README.md).
The existing wall-clock UI captures continue to provide whole-frame and logical
state comparisons. Live-window tests use the platform clock.
