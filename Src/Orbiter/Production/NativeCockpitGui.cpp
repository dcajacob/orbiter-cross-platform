// Copyright (c) Martin Schweiger
// Licensed under the MIT License
// Native dialog services surrounding the original Select/InputBox algorithms.
#include "Select.h"
#include "CockpitGuiExports.h"
#include "NativeGraphics.h"
#include "imgui_internal.h"
#include <unordered_map>
#include <stdexcept>
using namespace orbiter::production;
ImGuiDialog::~ImGuiDialog() {
    auto& context=GetNativeRenderContext();
    if(context.cockpitSelect==this)context.cockpitSelect=nullptr;
    if(context.cockpitInput==this)context.cockpitInput=nullptr;
}
bool ImGuiDialog::HandleHelpButton() {
    if(helpfile.empty())return false;
    if(ImGui::Button("Help"))throw std::runtime_error("Native compiled-help viewer is unavailable");
    return true;
}
void ImGuiDialog::Display() {
    ImGui::SetNextWindowSize(ImVec2(defaultSize.width,defaultSize.height),ImGuiCond_FirstUseEver);
    if(ImGui::Begin(name.c_str(),&active)){HandleHelpButton();OnDraw();}
    ImGui::End();if(!active)OnClose();
}
void ImGuiDialog::Activate() {active=true;ImGui::SetWindowFocus(name.c_str());}
namespace ImGui {
	struct FadingState
	{
		enum State { Closed, Opening, Open } state = Closed;
		float animstate = 0.0f;
	};
	static std::unordered_map<ImGuiID, FadingState> g_popupStates;

	// A popup that will fade-in when open (making it fade-out is too tricky)
	ORBITER_PRODUCTION_API bool BeginAnimatedPopup(const char* name, float duration)
	{
		ImGuiContext& g = *GImGui;
		ImGuiID id = g.CurrentWindow->GetID(name);
		FadingState& S = g_popupStates[id];

		if (ImGui::IsPopupOpen(name) && S.state == FadingState::Closed)	{
			S.state = FadingState::Opening;
			S.animstate = 0.0f;
		}

		if (S.state == FadingState::Opening) {
			S.animstate += ImGui::GetIO().DeltaTime;
			if (S.animstate >= duration)
				S.state = FadingState::Open;
		}

		float x = ImClamp(S.animstate / duration, 0.0f, 1.0f);
		float alpha = x * x * (3.0f - 2.0f * x);

		ImGui::PushStyleVar(ImGuiStyleVar_Alpha, alpha);

		if (!ImGui::BeginPopup(name)) {
			ImGui::PopStyleVar();
			S.state = FadingState::Closed;
			return false;
		}

		return true;
	}

	ORBITER_PRODUCTION_API void EndAnimatedPopup()
	{
		ImGui::PopStyleVar();
		ImGui::EndPopup();
	}

}
