// Copyright (c) Martin Schweiger
// Licensed under the MIT License

// ======================================================================
// Custom function selection dialog
// ======================================================================

#include "DlgFunction.h"
#ifdef _WIN32
#include "Orbiter.h"
#include "VesselAPI.h"
extern Orbiter* g_pOrbiter;
#else
#include "Production/NativeGraphics.h"
#include "Production/NativeRenderApi.h"
#endif
#include "Production/CustomCommands.h"
#include "imgui.h"
#include "IconsFontAwesome6.h"
#include <algorithm>
#include <iterator>

namespace {
constexpr struct Lesson {
    const char* title;
    const char* instruction;
} lessons[] = {
    {"Pause and resume", "Choose Pause in the flight menu. Watch the clock stop or start, then choose Pause again."},
    {"Look around", "Switch between the cockpit and the outside view. The default key is F1. Switch back when you are ready."},
    {"Control time", "Open Speed in the flight menu. Try 0.1x to slow time down, then choose 1x to return to real time."},
    {"Read main thrust", "In free flight, gently raise the main throttle and bring it back to idle. Watch the engine level below."}
};
}

class FlightTutorial final : public ImGuiDialog {
public:
    FlightTutorial() : ImGuiDialog("Flight tutorial") {}

    void Display() override {
        const auto* viewport = ImGui::GetMainViewport();
        const float em = ImGui::GetFontSize();
        const float width = std::min(22 * em, viewport->WorkSize.x - em);
        ImGui::SetNextWindowPos({viewport->WorkPos.x + viewport->WorkSize.x - em,
            viewport->WorkPos.y + 4 * em}, ImGuiCond_FirstUseEver, {1, 0});
        ImGui::SetNextWindowSize({width, 0});
        ImGui::SetNextWindowSizeConstraints({width, 0}, {width, viewport->WorkSize.y});
        if (ImGui::Begin(name.c_str(), &active, ImGuiWindowFlags_NoCollapse |
            ImGuiWindowFlags_NoSavedSettings | ImGuiWindowFlags_NoNav |
            ImGuiWindowFlags_NoFocusOnAppearing | ImGuiWindowFlags_AlwaysAutoResize)) {
            OnDraw();
        }
        ImGui::End();
        if (!active) step = 0;
    }

private:
    int step = 0;
    void OnDraw() override {
        constexpr int count = static_cast<int>(std::size(lessons));
        ImGui::Text("%d of %d   %s", step + 1, count, lessons[step].title);
        ImGui::Separator();
        const auto* vessel = oapiGetFocusInterface();
        const bool hasMain = step == 3 && vessel && vessel->GetGroupThrusterCount(THGROUP_MAIN);
        if (step == 3 && !hasMain)
            ImGui::TextWrapped("This vessel has no standard main engine group. You can try this lesson in a Delta-glider.");
        else
            ImGui::TextWrapped("%s", lessons[step].instruction);
        ImGui::Spacing();
        switch (step) {
        case 0: ImGui::TextUnformatted(oapiGetPause() ? "Flight paused" : "Flight running"); break;
        case 1: ImGui::TextUnformatted(oapiCameraInternal() ? "Cockpit view" : "Outside view"); break;
        case 2: ImGui::Text("Time acceleration: %gx", oapiGetTimeAcceleration()); break;
        case 3:
            if (hasMain) ImGui::Text("Main thrust: %.1f%%", 100 * vessel->GetThrusterGroupLevel(THGROUP_MAIN));
            break;
        }
        ImGui::Spacing();
        const bool last = step == count - 1;
        ImGui::BeginDisabled(step == 0);
        if (ImGui::Button("Back")) --step;
        ImGui::EndDisabled();
        ImGui::SameLine();
        if (ImGui::Button(last ? "Done" : "Next")) {
            if (last) active = false;
            else ++step;
        }
    }
};

#ifdef _WIN32
std::vector<orbiter::production::CustomCommand> DlgFunction::CommandsForDisplay() {
    std::vector<orbiter::production::CustomCommand> commands;
    for(DWORD i=0;i<g_pOrbiter->ncustomcmd;++i) {
        const auto& entry=g_pOrbiter->customcmd[i];
        commands.push_back({entry.id,entry.label,entry.desc ? entry.desc : "",entry.func,entry.context});
    }
    return commands;
}
bool DlgFunction::CommandPresent(int id) {
    for(DWORD i=0;i<g_pOrbiter->ncustomcmd;++i)if(g_pOrbiter->customcmd[i].id==id)return true;
    return false;
}
void DlgFunction::InvokeCommand(int id) {
    for(DWORD i=0;i<g_pOrbiter->ncustomcmd;++i)if(g_pOrbiter->customcmd[i].id==id) {
        const auto callback=g_pOrbiter->customcmd[i].func;
        void* context=g_pOrbiter->customcmd[i].context;
        callback(context);return;
    }
}
#else
static auto& Commands() {return orbiter::production::GetNativeRenderContext().customCommands;}
std::vector<orbiter::production::CustomCommand> DlgFunction::CommandsForDisplay() {return Commands().Snapshot();}
bool DlgFunction::CommandPresent(int id) {return Commands().Contains(id);}
void DlgFunction::InvokeCommand(int id) {Commands().Invoke(id);}
#endif

DlgFunction::DlgFunction() : ImGuiDialog(ICON_FA_PUZZLE_PIECE " Orbiter: Custom functions", {340, 290}) {
	SetHelp("html/orbiter.chm", "/customcmd.htm");
}
DlgFunction::~DlgFunction() = default;

void DlgFunction::OnDraw() {
	ImVec2 button_sz(ImVec2(ImGui::GetContentRegionAvail().x, 20));
    for (const auto& command : CommandsForDisplay()) {
        if(!CommandPresent(command.id))continue;
        ImGui::PushID(command.id);
	    if(ImGui::Button(command.label.c_str(), button_sz)) {
            InvokeCommand(command.id);
        }
        if (ImGui::IsItemHovered())
        {
            ImGui::BeginTooltip();
            ImGui::PushTextWrapPos(ImGui::GetFontSize() * 35.0f);
            ImGui::TextUnformatted(command.description.c_str());
            ImGui::PopTextWrapPos();
            ImGui::EndTooltip();
        }
        ImGui::PopID();
    }
    ImGui::Separator();
    if (ImGui::Button("Flight tutorial", button_sz)) {
        if (!tutorial) tutorial = std::make_unique<FlightTutorial>();
        oapiOpenDialog(tutorial.get());
        active = false;
        ImGui::SetWindowFocus(static_cast<const char*>(nullptr));
    }
}
