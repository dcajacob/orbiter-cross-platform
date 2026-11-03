// Licensed under the MIT License
// Read-only public SDK observations, shared by the original and native probes.
#pragma once
#include "../../StockVessels/Observation.h"
#include <cmath>

namespace shuttle_a_controls {
using stock_vessels::require;
using stock_vessels::csv;
inline void headers(std::ofstream& state, std::ofstream& docks, std::ofstream& cockpit,
                    std::ofstream& animations, std::ofstream& attachments) {
    stock_vessels::headers(state, docks);
    stock_vessels::open(cockpit, "shuttle-a-cockpit.csv", "tick,object,class,cockpit");
    stock_vessels::open(animations, "shuttle-a-animations.csv", "tick,object,index,state");
    stock_vessels::open(attachments, "stock-vessel-attachments.csv",
        "tick,object,parent,index,id,x,y,z,dx,dy,dz,rx,ry,rz,attached");
}
inline void snapshot(std::ofstream& state, std::ofstream& docks, std::ofstream& cockpit,
                     std::ofstream& animations, std::ofstream& attachments, unsigned tick) {
    stock_vessels::snapshot(state, docks, tick);
    auto* focus = oapiGetFocusInterface();
    require(focus && std::string(focus->GetName()) == "SH-15", "Stock Shuttle-A focus missing");
    require(oapiCameraInternal() && (oapiCockpitMode() == 2 || oapiCockpitMode() == 3),
            "Stock Shuttle-A cockpit missing");
    cockpit << tick << ',' << csv(focus->GetName()) << ',' << csv(focus->GetClassName())
            << ',' << oapiCockpitMode() << '\n';
    // Original construction order: both engine pods, hatch, two airlocks, gear.
    for (unsigned index = 0; index < 6; ++index) {
        const double value = focus->GetAnimation(index);
        require(std::isfinite(value) && value >= 0 && value <= 1, "Stock animation missing");
        animations << tick << ',' << csv(focus->GetName()) << ',' << index << ',' << value << '\n';
    }
    for (unsigned object = 0; object < oapiGetVesselCount(); ++object) {
        auto* vessel = oapiGetVesselInterface(oapiGetVesselByIndex(object));
        require(vessel != nullptr, "Stock attachment vessel missing");
        for (bool parent : {false, true}) for (unsigned index = 0; index < vessel->AttachmentCount(parent); ++index) {
            auto port = vessel->GetAttachmentHandle(parent, index);
            VECTOR3 p{}, d{}, r{};
            vessel->GetAttachmentParams(port, p, d, r);
            auto other = vessel->GetAttachmentStatus(port);
            auto* peer = other ? oapiGetVesselInterface(other) : nullptr;
            attachments << tick << ',' << csv(vessel->GetName()) << ',' << parent << ',' << index
                        << ',' << csv(vessel->GetAttachmentId(port));
            for (double value : {p.x,p.y,p.z,d.x,d.y,d.z,r.x,r.y,r.z}) attachments << ',' << value;
            attachments << ',' << csv(peer ? peer->GetName() : "") << '\n';
        }
    }
    cockpit.flush(); animations.flush(); attachments.flush();
}
}
