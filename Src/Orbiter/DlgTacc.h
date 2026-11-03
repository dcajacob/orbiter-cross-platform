// Copyright (c) Martin Schweiger
// Licensed under the MIT License

// ======================================================================
// Time acceleration dialog
// ======================================================================

#ifndef __DLGTACC_H
#define __DLGTACC_H

#ifdef _WIN32
#include "OrbiterAPI.h"
#else
#include "NativeVesselAPI.h"
#endif

class DlgTacc : public ImGuiDialog {
public:
    DlgTacc();
    void OnDraw() override;
};

#endif // !__DLGTACC_H