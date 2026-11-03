// Copyright (c) Martin Schweiger
// Licensed under the MIT License

// ======================================================================
// Menu bar configuration dialog
// ======================================================================

#ifndef __DLGMENUCFG_H
#define __DLGMENUCFG_H

#ifdef _WIN32
#include "OrbiterAPI.h"
#else
#include "NativeVesselAPI.h"
#endif

class DlgMenuCfg: public ImGuiDialog {
public:
	DlgMenuCfg ();
	void OnDraw();
};

#endif // !__DLGMENUCFG_H