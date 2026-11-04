// Licensed under the MIT License
// Passive public SDK observations, including shared tanks and non-focus payloads.
#pragma once
#include "../StockVessels/Observation.h"
#include <map>
#include <utility>

namespace remaining_stock {
struct Details {
    std::ofstream population,propellants,thrusters,attachments,playback,meshes;
    void open() {
        using stock_vessels::open;
        open(population,"stock-population.csv","tick,count");
        open(propellants,"stock-vessel-propellants.csv","tick,object,index,mass,max_mass,efficiency");
        open(thrusters,"stock-vessel-thrusters.csv","tick,object,index,x,y,z,dx,dy,dz,max_thrust,isp0,level,resource_object,resource_index");
        open(attachments,"stock-vessel-attachments.csv","tick,object,to_parent,index,id,x,y,z,dx,dy,dz,rx,ry,rz,attached");
        open(playback,"stock-playback.csv","tick,object,playback");
        open(meshes,"stock-vessel-meshes.csv","tick,object,index,present,template,name,visibility,x,y,z");
    }
    void snapshot(unsigned tick) {
        using stock_vessels::csv;
        using stock_vessels::require;
        const auto count=oapiGetVesselCount();
        population<<tick<<','<<count<<'\n';
        std::map<PROPELLANT_HANDLE,std::pair<std::string,unsigned>> resources;
        for(unsigned i=0;i<count;++i) {
            auto* vessel=oapiGetVesselInterface(oapiGetVesselByIndex(i));
            require(vessel!=nullptr,"Remaining stock vessel missing");
            for(unsigned j=0;j<vessel->GetPropellantCount();++j) {
                auto handle=vessel->GetPropellantHandleByIndex(j);
                require(handle!=nullptr && resources.emplace(handle,std::make_pair(std::string(vessel->GetName()),j)).second,
                        "Duplicate or missing public propellant resource");
                propellants<<tick<<','<<csv(vessel->GetName())<<','<<j<<','<<vessel->GetPropellantMass(handle)
                    <<','<<vessel->GetPropellantMaxMass(handle)<<','<<vessel->GetPropellantEfficiency(handle)<<'\n';
            }
        }
        for(unsigned i=0;i<count;++i) {
            auto* vessel=oapiGetVesselInterface(oapiGetVesselByIndex(i));
            playback<<tick<<','<<csv(vessel->GetName())<<','<<vessel->Playback()<<'\n';
            for(unsigned j=0;j<vessel->GetMeshCount();++j) {
                auto cached=vessel->GetMeshTemplate(j);const char* name=vessel->GetMeshName(j);
                const bool present=cached || name;VECTOR3 offset{};
                if(present)require(vessel->GetMeshOffset(j,offset),"Present mesh offset missing");
                meshes<<tick<<','<<csv(vessel->GetName())<<','<<j<<','<<present<<','<<(cached!=nullptr)
                    <<','<<csv(name?name:"")<<','<<(present?vessel->GetMeshVisibilityMode(j):0)
                    <<','<<offset.x<<','<<offset.y<<','<<offset.z<<'\n';
            }
            for(unsigned j=0;j<vessel->GetThrusterCount();++j) {
                auto handle=vessel->GetThrusterHandleByIndex(j);
                require(handle!=nullptr,"Public thruster missing");
                VECTOR3 p{},d{};vessel->GetThrusterRef(handle,p);vessel->GetThrusterDir(handle,d);
                thrusters<<tick<<','<<csv(vessel->GetName())<<','<<j;
                for(double value:{p.x,p.y,p.z,d.x,d.y,d.z,vessel->GetThrusterMax0(handle),
                                  vessel->GetThrusterIsp0(handle),vessel->GetThrusterLevel(handle)})thrusters<<','<<value;
                auto fuel=vessel->GetThrusterResource(handle);
                if(fuel) {
                    auto found=resources.find(fuel);require(found!=resources.end(),"Thruster tank absent from complete public vessel population");
                    thrusters<<','<<csv(found->second.first.c_str())<<','<<found->second.second;
                } else thrusters<<",\"\",-1";
                thrusters<<'\n';
            }
            for(bool parent:{false,true}) {
                for(unsigned j=0;j<vessel->AttachmentCount(parent);++j) {
                    auto handle=vessel->GetAttachmentHandle(parent,j);
                    require(handle!=nullptr,"Public attachment missing");
                    VECTOR3 p{},d{},r{};vessel->GetAttachmentParams(handle,p,d,r);
                    const char* id=vessel->GetAttachmentId(handle);
                    attachments<<tick<<','<<csv(vessel->GetName())<<','<<parent<<','<<j<<','<<csv(id?id:"");
                    for(double value:{p.x,p.y,p.z,d.x,d.y,d.z,r.x,r.y,r.z})attachments<<','<<value;
                    auto other=vessel->GetAttachmentStatus(handle);
                    auto* peer=other?oapiGetVesselInterface(other):nullptr;
                    attachments<<','<<csv(peer?peer->GetName():"")<<'\n';
                }
            }
        }
        population.flush();propellants.flush();thrusters.flush();attachments.flush();playback.flush();meshes.flush();
    }
};
}
