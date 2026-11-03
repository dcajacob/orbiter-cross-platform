// Copyright (c) Martin Schweiger
// Licensed under the MIT License

// ======================================================================
// Menu bar configuration dialog
// ======================================================================

#include "DlgMenuCfg.h"
#include "MenuInfoBar.h"
#ifdef _WIN32
#include "Pane.h"
#endif
#include "imgui.h"
#ifdef _WIN32
#include "imgui_extras.h"
#else
#include "Production/CockpitGuiExports.h"
#endif
#ifdef _WIN32
#include "Orbiter.h"
#else
#include "Production/NativeGraphics.h"
#include "Production/NativeCockpitUi.h"
#include "Config.h"
#endif
#include "IconsFontAwesome6.h"

#ifdef _WIN32
extern Orbiter *g_pOrbiter;
extern Pane *g_pane;
#endif

DlgMenuCfg::DlgMenuCfg(): ImGuiDialog(ICON_FA_SLIDERS " Orbiter: Configure menu bars")
{
	SetHelp("html/orbiter.chm", "/menucfg.htm");
}

void DlgMenuCfg::OnDraw()
{
	const char *modes[] = {"Show", "Hide", "Auto-hide"};

#ifdef _WIN32
	CFG_UIPRM &prm = g_pOrbiter->Cfg()->CfgUIPrm;
	MenuInfoBar *mib = g_pane->MIBar();
#else
    auto& prm=orbiter::production::GetNativeRenderContext().configuration->CfgUIPrm;
    auto* mib=&orbiter::production::CockpitMenuBar();
#endif

	if(ImGui::BeginTabBar("##MenuCfgTab")) {
		if(ImGui::BeginTabItem("Appearance")) {
			ImGui::BeginChild("##Child");
			ImGui::SeparatorText("Menu bar");
			ImGui::PushID(1);
			ImGui::RadioButton("Show", &prm.MenuMode, 0);
			ImGui::SameLine();
			ImGui::RadioButton("Hide", &prm.MenuMode, 1);
			ImGui::SameLine();
			ImGui::RadioButton("Auto-hide", &prm.MenuMode, 2);

			ImGui::Checkbox("Always show labels", &prm.bMenuLabelAlways);
			ImGui::SliderInt("Opacity", &prm.MenuOpacity, 0, 10);
			ImGui::SliderInt("Animation speed", &prm.MenuScrollspeed, 1, 20);
			ImGui::SliderInt("Button size", &prm.MenuButtonSize, 10, 64);
			ImGui::SliderInt("Hovered size", &prm.MenuButtonHoverSize, 10, 64);
			ImGui::SliderInt("Spacing", &prm.MenuButtonSpacing, 1, 32);
			ImGui::PopID();

			ImGui::SeparatorText("Info bars");
			ImGui::PushID(2);
			ImGui::RadioButton("Show", &prm.InfoMode, 0);
			ImGui::SameLine();
			ImGui::RadioButton("Hide", &prm.InfoMode, 1);
			ImGui::SameLine();
			ImGui::RadioButton("Auto-hide", &prm.InfoMode, 2);
			ImGui::Checkbox("Always show warp factor", &prm.bWarpAlways);
			ImGui::SliderInt("Opacity", &prm.InfoOpacity, 0, 10);
			ImGui::PopID();

			ImGui::SeparatorText("FPS info bar");
			const char *fpsmode[]={"None", "On the left", "On the right"};
			ImGui::Combo("##FPSMode", &prm.FPS, fpsmode, IM_ARRAYSIZE(fpsmode));

			ImGui::EndChild();
			ImGui::EndTabItem();
		}
		if(ImGui::BeginTabItem("Menu items")) {
			ImGui::BeginChild("##Child");
			bool changed = false;
			for(auto &pref: mib->GetPreferences()) {
				changed |= ImGui::Checkbox(pref.label.c_str(), &pref.enabled);
			}
			if(changed)
				mib->SyncPreferences();
			ImGui::EndChild();
			ImGui::EndTabItem();  
		}
		ImGui::EndTabBar();
	}
}
