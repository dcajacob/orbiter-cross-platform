// Licensed under the MIT License
// Test observer for the native renderer. Forward the real registration before
// exercising the SDK on a live visual in the stock ShuttlePB scene.
#include "Production/NativeGraphics.h"
#include "NativeVesselAPI.h"
#include "Instrument.h"
#include "meshres_vc.h"
#include "OrbiterCameraData.h"
#include <cmath>
#include <cstring>
#include <dlfcn.h>
#include <fstream>
#include <stdexcept>

void OpenCustomMFDProbe();

using namespace orbiter::production;

namespace {
void require(bool condition, const char *message)
{
    if (!condition) throw std::runtime_error(message);
}

void exercise(VESSEL &vessel, VISHANDLE visual)
{
    auto object = vessel.GetHandle();
    char name[] = "PB";
    require(oapiGetObjectByName(name) == object && oapiGetFocusObject() == object, "Stock focus lookup differs");
    require(oapiCockpitMode() == COCKPIT_GENERIC, "Stock generic cockpit mode unavailable");
    require(std::abs(oapiTime2MJD(oapiGetSimTime()) - oapiGetSimMJD()) <= 1e-10, "Simulation clocks disagree");
    double valueRead;
    require(oapiGetPitch(object, &valueRead) && valueRead == vessel.GetPitch() &&
            oapiGetBank(object, &valueRead) && valueRead == vessel.GetBank() &&
            oapiGetAltitude(object, &valueRead) && valueRead == vessel.GetAltitude(), "Stock flight attitude or altitude differs");
    auto tank = oapiGetPropellantHandle(object, 0);
    require(tank && tank == vessel.GetPropellantHandleByIndex(0) &&
            oapiGetPropellantMass(tank) == vessel.GetPropellantMass(tank) &&
            oapiGetEmptyMass(object) == vessel.GetEmptyMass() &&
            !oapiGetPropellantHandle(object, vessel.GetPropellantCount()), "Stock propellant lookup differs");
    for (auto frame : {FRAME_GLOBAL, FRAME_LOCAL, FRAME_REFLOCAL, FRAME_HORIZON}) {
        VECTOR3 sdk{}, api{};
        require(oapiGetGroundspeedVector(object, frame, &sdk) && vessel.GetGroundspeedVector(frame, api) &&
                sdk.x == api.x && sdk.y == api.y && sdk.z == api.z, "Stock ground velocity differs");
        require(oapiGetAirspeedVector(nullptr, frame, &sdk) && vessel.GetAirspeedVector(frame, api) &&
                sdk.x == api.x && sdk.y == api.y && sdk.z == api.z, "Stock focus air velocity differs");
    }
    AnimState2 gear(0.5);
    gear.Open();
    require(gear.Process(0.25) && gear.State() == 0.125, "Stock animation state did not advance");
    const auto scenario = GetNativeRenderContext().evidence / "animation.scn";
    {
        std::ofstream stream(scenario);
        stream.exceptions(std::ios::badbit | std::ios::failbit);
        gear.SaveState(&stream, "GEAR");
    }
    std::string line;
    std::ifstream saved(scenario);
    std::getline(saved, line);
    AnimState2 restored(0.5);
    require(line == "  GEAR 0.1250 0.5000" && restored.ParseScenarioLine(line.c_str()+2, "gear") &&
            restored.State() == gear.State() && restored.Speed() == gear.Speed(), "Stock animation scenario round trip failed");
    restored.Close();
    require(restored.Process(0.25) && restored.IsClosed() && !restored.IsActive(), "Restored actuator did not close");

    auto mesh = oapiLoadMeshGlobal("DG\\deltaglider_vc");
    require(mesh && oapiMeshGroupCount(mesh) == NGRP_VC, "Stock DG virtual cockpit template missing");
    auto index = vessel.AddMesh(mesh);
    auto device = vessel.GetDevMesh(visual, index);
    require(device && !vessel.GetDevMesh(visual, index + 1), "Visual mesh lookup failed");

    auto *group = oapiMeshGroup(mesh, GRP_HORIZON_VC);
    require(group && group->nVtx > 1, "Stock horizon group missing");
    oapi::UInt16 vertex = 1;
    NTVERTEX value{};
    GROUPREQUESTSPEC request{};
    request.Vtx = &value;
    request.nVtx = 1;
    request.VtxPerm = &vertex;
    require(oapiGetMeshGroup(device, GRP_HORIZON_VC, &request) == 0 &&
            value.tu == group->Vtx[vertex].tu, "Stock horizon vertex read failed");
    const auto before = value;
    value.tu += 0.125f;
    GROUPEDITSPEC edit{};
    edit.flags = GRPEDIT_VTXTEXU;
    edit.Vtx = &value;
    edit.nVtx = 1;
    edit.vIdx = &vertex;
    require(oapiEditMeshGroup(device, GRP_HORIZON_VC, &edit) == 0, "Stock horizon vertex edit failed");
    value = {};
    require(oapiGetMeshGroup(device, GRP_HORIZON_VC, &request) == 0 &&
            value.tu == before.tu + 0.125f && value.tv == before.tv && group->Vtx[vertex].tu == before.tu,
            "Visual edit changed the wrong attribute or shared template");
    require(oapiEditMeshGroup(device, ~0u, &edit) == 1 && oapiGetMeshGroup(device, ~0u, &request) == 1,
            "Invalid mesh group index accepted");
    value = before;
    require(oapiEditMeshGroup(device, GRP_HORIZON_VC, &edit) == 0, "Stock horizon restore failed");
    const auto *material = oapiMeshMaterial(mesh, 14);
    require(oapiSetMaterial(device, 14, material) == 0 && oapiSetMaterial(device, NMAT_VC, material) == 4,
            "Stock panel material selection failed");
    require(oapiSetTexture(device, 17, oapiGetTextureHandle(mesh, 17)) && !oapiSetTexture(device, ~0u, nullptr),
            "Stock VC texture selection failed");

    require(vessel.DelMesh(index), "VC instance deletion failed");
    VECTOR3 offset{};
    vessel.SetMeshVisibilityMode(index, MESHVIS_ALWAYS);
    require(!vessel.GetMeshName(index) && !vessel.GetMeshTemplate(index) && !vessel.CopyMeshFromTemplate(index) &&
            !vessel.GetDevMesh(visual, index) && !vessel.GetMeshOffset(index, offset) && !vessel.GetMeshVisibilityMode(index),
            "Deleted mesh slot still accessible");
    auto reused = vessel.AddMesh(mesh);
    require(reused == index && vessel.GetDevMesh(visual, reused) && vessel.DelMesh(reused), "Mesh slot reuse failed");
    std::ofstream report(GetNativeRenderContext().evidence / "stock-vc-mesh.json");
    report.exceptions(std::ios::badbit | std::ios::failbit);
    report << "{\"stock_groups\":" << NGRP_VC << ",\"horizon_group\":" << GRP_HORIZON_VC
           << ",\"instance_edit\":true,\"template_isolated\":true,\"slot_reused\":true}\n";
}
}

void orbiter::production::RenderRegisterVisual(OBJHANDLE object, VISHANDLE visual)
{
    // This module is preloaded only in the test process. Linux uses the Itanium
    // C++ ABI for the existing native renderer registration function.
    auto original = reinterpret_cast<decltype(&RenderRegisterVisual)>(
        dlsym(RTLD_NEXT, "_ZN7orbiter10production20RenderRegisterVisualEPvS1_"));
    require(original, "Production renderer registration function unavailable");
    original(object, visual);
    if (oapiGetObjectType(object) == OBJTP_VESSEL) {
        auto *vessel = oapiGetVesselInterface(object);
        if (!std::strcmp(vessel->GetClassName(), "ShuttlePB")) {
            exercise(*vessel, visual);
            OpenCustomMFDProbe();
        }
    }
}
