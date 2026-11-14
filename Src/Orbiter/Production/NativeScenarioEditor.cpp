// Licensed under the MIT License
#include "NativeCockpitUi.h"

#ifdef __linux__
#include "NativeGraphics.h"
#include "NativeInterpreterSdk.h"
#include "Base.h"
#include "Planet.h"
#include "PsysCore.h"
#include "Text.h"
#include "Vessel.h"
#include "imgui.h"
#include <algorithm>
#include <cmath>
#include <iterator>
#include <memory>
#include <string>

namespace orbiter::production {
namespace {
constexpr const char* stockClasses[] = {"ShuttlePB", "DeltaGlider"};
constexpr const char* stockLabels[] = {"Shuttle PB", "Delta-glider"};

bool Connected(Vessel& vessel)
{
    if (vessel.SuperStruct() || vessel.isAttached()) return true;
    auto* sdk = vessel.GetModuleInterface();
    for (bool parent : {false, true})
        for (UInt32 i = 0; i < sdk->AttachmentCount(parent); ++i)
            if (sdk->GetAttachmentStatus(sdk->GetAttachmentHandle(parent, i))) return true;
    return false;
}

VESSELSTATUS2 StateOf(Vessel& vessel)
{
    VESSELSTATUS2 state{};
    state.version = 2;
    vessel.GetModuleInterface()->GetStatusEx(&state);
    return state;
}

bool ValidOrbit(const VESSELSTATUS2& state)
{
    const auto& body = *static_cast<const CelestialBody*>(state.rbody);
    Vector position(state.rpos.x, state.rpos.y, state.rpos.z);
    Vector velocity(state.rvel.x, state.rvel.y, state.rvel.z);
    const double radius = position.length();
    const double angularMomentum = crossp(position, velocity).length2();
    if (!std::isfinite(radius) || !(radius > 0) || !std::isfinite(velocity.length2()) ||
        !std::isfinite(angularMomentum) || !(angularMomentum > 0)) return false;
    double elevation = 0;
    if (body.Type() == OBJTP_PLANET) {
        double longitude, latitude, localRadius;
        body.LocalToEquatorial(tmul(body.GRot(), position), longitude, latitude, localRadius);
        elevation = static_cast<const Planet&>(body).Elevation(longitude, latitude);
    }
    return radius > body.Size() + elevation;
}

void ReleasePad(Vessel& vessel, const VESSELSTATUS2& state)
{
    auto* base = static_cast<Base*>(state.base);
    if (base) base->ClearPad(&vessel);
    if (auto* target = vessel.LandingTarget(); target && target != base)
        target->ClearPad(&vessel);
}

class ScenarioEditor final : public ImGuiDialog {
public:
    ScenarioEditor() : ImGuiDialog("Scenario editor", {430, 395}) {}

private:
    std::string selected;
    std::string feedback;
    char vesselName[64] = "NewVessel";
    int stockClass = 0;
    double placement[3]{};
    bool confirmRemove = false;

    void Select(Vessel& vessel)
    {
        selected = vessel.Name();
        confirmRemove = false;
        const auto state = StateOf(vessel);
        if (state.status == 1) {
            placement[0] = state.surf_lng * DEG;
            placement[1] = state.surf_lat * DEG;
            placement[2] = state.surf_hdg * DEG;
        } else {
            placement[0] = state.rpos.x;
            placement[1] = state.rpos.y;
            placement[2] = state.rpos.z;
        }
    }

    void Add(NativeRenderContext& context)
    {
        const std::string name = vesselName;
        const auto allowed = [](char c) {
            return (c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') ||
                   (c >= '0' && c <= '9') || c == '-' || c == '_';
        };
        if (name.empty() || !std::all_of(name.begin(), name.end(), allowed)) {
            feedback = "Use letters, digits, hyphens or underscores in the vessel name.";
            return;
        }
        if (context.world->GetObj(name.c_str(), true) || CompareText(name.c_str(), "END_SHIPS") == 0) {
            feedback = "Choose a unique vessel name.";
            return;
        }
        const char* type = stockClasses[stockClass];
        const std::string classFile = std::string(type) + ".cfg";
        if (!context.configurationFiles->Contains("Vessels/" + classFile) &&
            !context.configurationFiles->Contains(classFile)) {
            feedback = "The stock vessel configuration is missing.";
            return;
        }

        auto state = StateOf(*context.focus);
        state.base = nullptr;
        state.port = -1;
        state.xpdr = 0;
        if (state.status == 1) {
            // Spawn on the same body about 100 m north (south near the pole).
            const auto* body = static_cast<const Body*>(state.rbody);
            const double offset = 100.0 / body->Size();
            state.surf_lat += state.surf_lat > PI05 - offset ? -offset : offset;
            state.arot.x = 10; // Legacy status sentinel for default touchdown orientation.
        } else {
            Vector position(state.rpos.x, state.rpos.y, state.rpos.z);
            const double radius = position.length();
            if (!(radius > 0) || !std::isfinite(radius)) {
                feedback = "The focus vessel has no usable orbital position.";
                return;
            }
            // A radial offset keeps the new vessel above the same terrain point.
            const Vector next = position * (1.0 + (100.0 + context.focus->Size()) / radius);
            state.rpos = _V(next.x, next.y, next.z);
            state.vrot = _V(0, 0, 0);
            state.status = 0;
            if (!ValidOrbit(state)) {
                feedback = "The focus vessel has no usable orbital state.";
                return;
            }
        }
        try {
            auto* added = static_cast<Vessel*>(oapiCreateVesselEx(name.c_str(), type, &state));
            if (!added) {
                feedback = "Orbiter could not create the vessel.";
                return;
            }
            Select(*added);
            feedback = "Added " + name + ".";
        } catch (const std::exception& error) {
            feedback = error.what();
        }
    }

    void Move(Vessel& vessel)
    {
        auto state = StateOf(vessel);
        const auto finite = [](double value) { return std::isfinite(value); };
        if (!std::all_of(std::begin(placement), std::end(placement), finite)) {
            feedback = "Enter finite coordinates.";
            return;
        }
        if (state.status == 1) {
            if (std::abs(placement[0]) > 180 || std::abs(placement[1]) > 90 ||
                placement[2] < 0 || placement[2] >= 360) {
                feedback = "Use longitude ±180°, latitude ±90°, and heading from 0° to less than 360°.";
                return;
            }
            ReleasePad(vessel, state);
            state.base = nullptr;
            state.port = -1;
            state.surf_lng = placement[0] * RAD;
            state.surf_lat = placement[1] * RAD;
            state.surf_hdg = placement[2] * RAD;
            state.arot.x = 10;
        } else {
            state.rpos = _V(placement[0], placement[1], placement[2]);
            if (!ValidOrbit(state)) {
                feedback = "Choose a point above terrain that gives a valid orbit with the current velocity.";
                return;
            }
        }
        vessel.GetModuleInterface()->DefSetStateEx(&state);
        Select(vessel);
        feedback = "Moved " + selected + ".";
    }

    void DrawVessel(NativeRenderContext& context, Vessel& vessel)
    {
        if (Connected(vessel)) {
            ImGui::TextWrapped("Undock or detach this vessel before moving or removing it.");
            return;
        }
        const auto state = StateOf(vessel);
        ImGui::Text("Reference body: %s", static_cast<const Body*>(state.rbody)->Name());
        if (state.status == 1) {
            ImGui::InputDouble("Longitude (°)", &placement[0], 0.001, 0.01, "%.7f");
            ImGui::InputDouble("Latitude (°)", &placement[1], 0.001, 0.01, "%.7f");
            ImGui::InputDouble("Heading (°)", &placement[2], 1, 10, "%.2f");
        } else {
            ImGui::TextUnformatted("Ecliptic position in meters. Velocity is retained.");
            ImGui::InputDouble("X (m)", &placement[0], 100, 1000, "%.3f");
            ImGui::InputDouble("Y (m)", &placement[1], 100, 1000, "%.3f");
            ImGui::InputDouble("Z (m)", &placement[2], 100, 1000, "%.3f");
        }
        if (ImGui::Button("Move vessel")) Move(vessel);
        ImGui::SameLine();
        ImGui::BeginDisabled(&vessel == context.focus);
        if (ImGui::Button("Remove vessel")) confirmRemove = true;
        ImGui::EndDisabled();
        if (&vessel == context.focus) ImGui::TextWrapped("Switch focus to another vessel before removing this one.");
        if (confirmRemove && &vessel != context.focus) {
            ImGui::Text("Remove %s from this flight?", vessel.Name());
            if (ImGui::Button("Confirm removal")) {
                if (oapiDeleteVessel(&vessel, nullptr)) {
                    ReleasePad(vessel, state);
                    context.scenarioEditorRemoval = true;
                    feedback = "Removed " + selected + ".";
                    Select(*context.focus);
                } else feedback = "Orbiter could not remove the vessel.";
            }
            ImGui::SameLine();
            if (ImGui::Button("Cancel")) confirmRemove = false;
        }
    }

    void OnDraw() override
    {
        auto& context = GetNativeRenderContext();
        if (ImGui::Button("Close editor")) {
            active = false;
            confirmRemove = false;
            return;
        }
        ImGui::SameLine();
        ImGui::TextUnformatted("Close to quicksave (Ctrl+S) or reload (F5).");
        if (context.recordingFlight || context.playingFlight) {
            ImGui::TextWrapped("Stop recording or playback before editing.");
            return;
        }
        if (!context.paused) {
            if (ImGui::Button("Pause to edit")) oapiSetPause(true);
            return;
        }

        ImGui::SeparatorText("Add near focus vessel");
        ImGui::InputText("Name", vesselName, sizeof vesselName);
        ImGui::Combo("Stock class", &stockClass, stockLabels, IM_ARRAYSIZE(stockLabels));
        if (ImGui::Button("Add vessel")) Add(context);

        ImGui::SeparatorText("Edit vessel");
        auto* vessel = context.world->GetVessel(selected.c_str(), true);
        if (!vessel || vessel->KillPending()) Select(*context.focus);
        if (ImGui::BeginCombo("Vessel", selected.c_str())) {
            for (auto* candidate : context.world->GetVessels())
                if (!candidate->KillPending() && ImGui::Selectable(candidate->Name(), candidate->Name() == selected)) {
                    Select(*candidate);
                    feedback.clear();
                }
            ImGui::EndCombo();
        }
        vessel = context.world->GetVessel(selected.c_str(), true);
        if (vessel && !vessel->KillPending()) DrawVessel(context, *vessel);
        if (!feedback.empty()) ImGui::TextWrapped("%s", feedback.c_str());
    }
};

std::unique_ptr<ScenarioEditor> editor;
}

void OpenCockpitScenarioEditor()
{
    if (!editor) editor = std::make_unique<ScenarioEditor>();
    oapiOpenDialog(editor.get());
}

void DestroyCockpitScenarioEditor() { editor.reset(); }
bool CockpitScenarioEditorActive() { return editor && editor->IsActive(); }
}
#else
namespace orbiter::production {
void OpenCockpitScenarioEditor() {}
void DestroyCockpitScenarioEditor() {}
bool CockpitScenarioEditorActive() { return false; }
}
#endif
