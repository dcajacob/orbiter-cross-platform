// Copyright (c) Martin Schweiger
// Licensed under the MIT License

// ======================================================================
// Custom function selection dialog
// ======================================================================

#include "DlgFunction.h"
#ifdef _WIN32
#include "Orbiter.h"
extern Orbiter* g_pOrbiter;
#else
#include "Production/NativeGraphics.h"
#endif
#include "Production/CustomCommands.h"
#include "imgui.h"
#include "IconsFontAwesome6.h"

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
}
