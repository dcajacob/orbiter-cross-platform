// Licensed under the MIT License
#pragma once
#include "Export.h"
namespace orbiter::production {
void CreateCockpitInfoBars();
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
