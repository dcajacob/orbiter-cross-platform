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

class DlgFunction : public ImGuiDialog {
public:
    DlgFunction();
    void OnDraw() override;
};
#endif // !__DLGFUNCTION_H
