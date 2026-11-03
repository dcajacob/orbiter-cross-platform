// Copyright (c) Martin Schweiger
// Licensed under the MIT License

// ======================================================================
// Focus vessel selection dialog
// ======================================================================

#include "DlgFocus.h"
#include "Psys.h"
#ifdef _WIN32
#include "OrbiterAPI.h"
#include "Orbiter.h"
#else
#include "Vessel.h"
#include "Production/NativeGraphics.h"
#include "Production/VesselLifetime.h"
#endif
#include "Camera.h"
#include "imgui.h"
#include <map>
#include "IconsFontAwesome6.h"

#ifdef _WIN32
extern Camera *g_camera;
extern PlanetarySystem *g_psys;
extern Orbiter *g_pOrbiter;
extern Vessel *g_pfocusobj;
static PlanetarySystem* FocusWorld() { return g_psys; }
static Camera* FocusCamera() { return g_camera; }
static Vessel* PriorFocus() { return g_pfocusobj; }
static void SelectFocus(Vessel* vessel) { g_pOrbiter->SetFocusObject(vessel); }
#else
using orbiter::production::GetNativeRenderContext;
static PlanetarySystem* FocusWorld() { return GetNativeRenderContext().world; }
static Camera* FocusCamera() { return GetNativeRenderContext().camera; }
static Vessel* PriorFocus() { return GetNativeRenderContext().lifetime->PreviousFocus(); }
static void SelectFocus(Vessel* vessel) { oapiSetFocusObject(vessel); }
#endif

DlgFocus::DlgFocus() : ImGuiDialog(ICON_FA_ROCKET " Orbiter: Select spacecraft", {300, 320}) {
	SetHelp("html/orbiter.chm", "/selvessel.htm");
}

void DlgFocus::OnDraw() {
    const char *tabs[] = {
        "All", "Nearby", "Location", "Class"
    };

    void (DlgFocus::* func[])() = {
        &DlgFocus::DrawAll, &DlgFocus::DrawNearby, &DlgFocus::DrawLocation, &DlgFocus::DrawClass
    };

    ImGuiTabBarFlags tab_bar_flags = ImGuiTabBarFlags_None;
    if (ImGui::BeginTabBar("FocusTabBar", tab_bar_flags))
    {
        for(size_t i = 0; i<sizeof(tabs)/sizeof(tabs[0]);i++) {
            if(ImGui::BeginTabItem(tabs[i])) {
                (this->*func[i])();
                ImGui::EndTabItem();
            }
        }
        ImGui::EndTabBar();
    }
}

void DlgFocus::DrawAll() {
    ImGuiWindowFlags window_flags =  ImGuiChildFlags_ResizeX;
    ImGui::BeginChild("ChildL", ImVec2(150, 0), 0, window_flags);
    ImGui::SeparatorText("Available targets");
	ImGui::BeginChild("ChildL_inner");
    for (int i = 0; i < FocusWorld()->nVessel(); i++) {
        Vessel *vessel = FocusWorld()->GetVessel(i);
        if (vessel->GetEnableFocus()) {
            std::string name = vessel->Name();
            const bool is_selected = m_SelectedShip == name;
            ImGuiTreeNodeFlags node_flags = ImGuiTreeNodeFlags_Leaf | ImGuiTreeNodeFlags_NoTreePushOnOpen;
            if(is_selected) node_flags |= ImGuiTreeNodeFlags_Selected;
            ImGui::TreeNodeEx(vessel->Name(), node_flags);
            if (ImGui::IsItemClicked() && !ImGui::IsItemToggledOpen()) {
                m_SelectedShip = vessel->Name();
            }
        }
	}

    ImGui::EndChild();
    ImGui::EndChild();
    ImGui::SameLine();
    ImGui::BeginChild("ChildR");
    ImGui::SeparatorText("Selected target");
    ImGui::TextUnformatted(m_SelectedShip.c_str());
    ImVec2 button_sz(ImVec2(ImGui::GetContentRegionAvail().x, 20));
    if(ImGui::Button("Select", button_sz)) {
        Vessel *vessel = FocusWorld()->GetVessel (m_SelectedShip.c_str(), true);
        if (vessel) {
            SelectFocus (vessel);
        }
    }
    if(ImGui::Button("Previous", button_sz)) {
        if (PriorFocus()) {
            SelectFocus (PriorFocus());
			m_SelectedShip = PriorFocus()->Name();
        }
    }
    ImGui::EndChild();
}
void DlgFocus::DrawNearby() {
    ImGuiWindowFlags window_flags = ImGuiChildFlags_ResizeX;
    ImGui::BeginChild("ChildL", ImVec2(150, 0), 0, window_flags);
    ImGui::SeparatorText("Available targets");
	ImGui::BeginChild("ChildL_inner");

    const Vector &campos = FocusCamera()->GPos();
    for (int i = 0; i < FocusWorld()->nVessel(); i++) {
        Vessel *vessel = FocusWorld()->GetVessel(i);
        if (vessel->GetEnableFocus()) {
            double dst = campos.dist (vessel->GPos());
			if (dst <= m_Range * 1000.0f) {
                std::string name = vessel->Name();
                const bool is_selected = m_SelectedShip == name;
                ImGuiTreeNodeFlags node_flags = ImGuiTreeNodeFlags_Leaf | ImGuiTreeNodeFlags_NoTreePushOnOpen;
                if(is_selected) node_flags |= ImGuiTreeNodeFlags_Selected;
                char cbuf[128];
                snprintf(cbuf,sizeof(cbuf),"%s (%.1fkm)", vessel->Name(), dst/1000.0f);
                ImGui::TreeNodeEx(cbuf, node_flags);
                if (ImGui::IsItemClicked() && !ImGui::IsItemToggledOpen()) {
                    m_SelectedShip = vessel->Name();
                }
            }
        }
	}

    ImGui::EndChild();
    ImGui::EndChild();
    ImGui::SameLine();
    ImGui::BeginChild("ChildR");
    ImGui::SeparatorText("Selected target");
    ImGui::TextUnformatted(m_SelectedShip.c_str());
    ImVec2 button_sz(ImVec2(ImGui::GetContentRegionAvail().x, 20));
    if(ImGui::Button("Select", button_sz)) {
        Vessel *vessel = FocusWorld()->GetVessel (m_SelectedShip.c_str(), true);
        if (vessel) {
            SelectFocus (vessel);
        }
    }
    if(ImGui::Button("Previous", button_sz)) {
        if (PriorFocus()) {
            SelectFocus (PriorFocus());
			m_SelectedShip = PriorFocus()->Name();
        }
    }

    ImGui::SetNextItemWidth(-FLT_MIN);
    if(ImGui::SliderFloat("##slider warp", &m_Range, 1.0f, 1000000.0f, "%.1fkm", ImGuiSliderFlags_Logarithmic)) {
    }

    ImGui::EndChild();
}
void DlgFocus::DrawLocation() {
    std::map<const char *, std::vector<Vessel *>> vesselMap; 
	for (int i = 0; i < FocusWorld()->nVessel(); i++) {
		Vessel *vessel = FocusWorld()->GetVessel(i);
		if (vessel->GetEnableFocus()) {
			const CelestialBody *ref = vessel->ElRef();
            vesselMap[ref->Name()].push_back(vessel);
        }
    }

    ImGuiWindowFlags window_flags =  ImGuiChildFlags_ResizeX;
    ImGui::BeginChild("ChildL", ImVec2(150,0), 0, window_flags);
    ImGui::SeparatorText("Available targets");
	ImGui::BeginChild("ChildL_inner");

    for(auto &kw : vesselMap) {
        if(ImGui::TreeNodeEx(kw.first)) {
            for(auto &vessel: kw.second) {
                const bool is_selected = m_SelectedShip == vessel->Name();
                ImGuiTreeNodeFlags node_flags = ImGuiTreeNodeFlags_Leaf | ImGuiTreeNodeFlags_NoTreePushOnOpen;
                if(is_selected) node_flags |= ImGuiTreeNodeFlags_Selected;
                ImGui::TreeNodeEx(vessel->Name(), node_flags);
                if (ImGui::IsItemClicked() && !ImGui::IsItemToggledOpen()) {
                    m_SelectedShip = vessel->Name();
                }
            }

            ImGui::TreePop();
        }
    }
    ImGui::EndChild();
    ImGui::EndChild();
    ImGui::SameLine();
    ImGui::BeginChild("ChildR");
    ImGui::SeparatorText("Selected target");
    ImGui::TextUnformatted(m_SelectedShip.c_str());
    ImVec2 button_sz(ImVec2(ImGui::GetContentRegionAvail().x, 20));
    if(ImGui::Button("Select", button_sz)) {
        Vessel *vessel = FocusWorld()->GetVessel (m_SelectedShip.c_str(), true);
        if (vessel) {
            SelectFocus (vessel);
        }
    }
    if(ImGui::Button("Previous", button_sz)) {
        if (PriorFocus()) {
            SelectFocus (PriorFocus());
			m_SelectedShip = PriorFocus()->Name();
        }
    }

    ImGui::EndChild();
}
void DlgFocus::DrawClass() {
    std::map<std::string, std::vector<Vessel *>> vesselMap; 
	for (int i = 0; i < FocusWorld()->nVessel(); i++) {
		Vessel *vessel = FocusWorld()->GetVessel(i);
		if (vessel->GetEnableFocus()) {
            vesselMap[vessel->ClassName()].push_back(vessel);
        }
    }

    ImGuiWindowFlags window_flags = ImGuiChildFlags_ResizeX;
    ImGui::BeginChild("ChildL", ImVec2(150,0), 0, window_flags);
    ImGui::SeparatorText("Available targets");
	ImGui::BeginChild("ChildL_inner");

    for(auto &kw : vesselMap) {
        if(ImGui::TreeNodeEx(kw.first.c_str())) {
            for(auto &vessel: kw.second) {
                const bool is_selected = m_SelectedShip == vessel->Name();
                ImGuiTreeNodeFlags node_flags = ImGuiTreeNodeFlags_Leaf | ImGuiTreeNodeFlags_NoTreePushOnOpen;
                if(is_selected) node_flags |= ImGuiTreeNodeFlags_Selected;
                ImGui::TreeNodeEx(vessel->Name(), node_flags);
                if (ImGui::IsItemClicked() && !ImGui::IsItemToggledOpen()) {
                    m_SelectedShip = vessel->Name();
                }
            }

            ImGui::TreePop();
        }
    }
    ImGui::EndChild();
    ImGui::EndChild();
    ImGui::SameLine();
    ImGui::BeginChild("ChildR");
    ImGui::SeparatorText("Selected target");
    ImGui::TextUnformatted(m_SelectedShip.c_str());
    ImVec2 button_sz(ImVec2(ImGui::GetContentRegionAvail().x, 20));
    if(ImGui::Button("Select", button_sz)) {
        Vessel *vessel = FocusWorld()->GetVessel (m_SelectedShip.c_str(), true);
        if (vessel) {
            SelectFocus (vessel);
        }
    }
    if(ImGui::Button("Previous", button_sz)) {
        if (PriorFocus()) {
            SelectFocus (PriorFocus());
			m_SelectedShip = PriorFocus()->Name();
        }
    }

    ImGui::EndChild();
}
