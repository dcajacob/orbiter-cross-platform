// Copyright (c) Martin Schweiger
// Licensed under the MIT License

// ======================================================================
// Custom function selection dialog
// ======================================================================

#ifndef __DLGFUNCTION_H
#define __DLGFUNCTION_H

#ifdef _WIN32
#include "OrbiterAPI.h"
#else
#include "NativeVesselAPI.h"
#endif
#include "Production/CustomCommands.h"
#include <memory>

class FlightTutorial;

class DlgFunction : public ImGuiDialog {
public:
    DlgFunction();
    ~DlgFunction() override;
    void OnDraw() override;
private:
    std::unique_ptr<FlightTutorial> tutorial;
    static std::vector<orbiter::production::CustomCommand> CommandsForDisplay();
    static bool CommandPresent(int id);
    static void InvokeCommand(int id);
};
#endif // !__DLGFUNCTION_H
