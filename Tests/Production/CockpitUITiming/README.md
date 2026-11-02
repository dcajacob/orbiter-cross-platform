# Fixed-clock original UI reference candidate

This additional fixture uses the preserved original Windows application, SDK,
renderer and original selection/input action schedule. A test-only ImGui
NewFramePre hook sets the frame delta to the same quarter-second step as the
physics fixture. It removes host-speed dependence from popup fades and caret
blinking. The original Select/InputBox implementations and ImGui drawing remain
in use. The observer records the clock setting in every run and removes its hook
at simulation end.

Existing wall-clock UI references remain frozen. These additional captures will
provide pixel references for deterministic UI timing in native regression tests.
All existing numerical and image budgets apply. Live-window tests continue to
exercise the normal platform clock. Acceptance requires both Windows builds,
fresh-process repeats, comparison and explicit provenance preservation.
