// Licensed under the MIT License
#pragma once
#include "Export.h"
#include "CoreTypes.h"
class MenuInfoBar;
class DlgInfo;
class Keymap;
namespace orbiter::production {
ORBITER_PRODUCTION_API bool HandleCockpitMenuKey(const Keymap&,UInt32,char*);
MenuInfoBar& CockpitMenuBar();
DlgInfo* OpenCockpitInfoDialog();
void CreateCockpitInfoBars();
void OpenCockpitPlaybackEditor();
ORBITER_PRODUCTION_API bool ToggleCockpitRecorder();
void DestroyCockpitInfoBars();
ORBITER_PRODUCTION_API void OpenCockpitFocusDialog();
ORBITER_PRODUCTION_API void CreateCockpitGui();
ORBITER_PRODUCTION_API void SetCockpitReplayClock(float seconds);
ORBITER_PRODUCTION_API void DestroyCockpitGui();
ORBITER_PRODUCTION_API void BeginCockpitGuiFrame();
ORBITER_PRODUCTION_API void ObserveCockpitGui(unsigned tick);
ORBITER_PRODUCTION_API bool CockpitGuiCapturesKeyboard();
ORBITER_PRODUCTION_API bool CockpitGuiCapturesMouse();
}
