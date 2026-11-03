// Licensed under the MIT License
// Read-only public SDK observations; no vessel or propagation setters.
#pragma once
#include <fstream>
#include <iomanip>
#include <locale>
#include <stdexcept>
#include <string>

namespace stock_vessels {
inline void require(bool value,const char* message) {
    if(!value)throw std::runtime_error(message);
}
inline std::string csv(const char* value) {
    std::string result="\"";
    for(const char* p=value;*p;++p) {if(*p=='\"')result+='\"';result+=*p;}
    return result+'\"';
}
inline void open(std::ofstream& stream,const char* path,const char* header) {
    stream.imbue(std::locale::classic());stream.exceptions(std::ios::badbit|std::ios::failbit);
    stream.open(path);stream<<std::setprecision(17)<<header<<'\n';
}
inline void headers(std::ofstream& state,std::ofstream& docks) {
    open(state,"stock-vessel-state.csv","tick,seconds,mjd,object,class,version,focus,enable_focus,x,y,z,vx,vy,vz,m11,m12,m13,m21,m22,m23,m31,m32,m33,wx,wy,wz,mass,empty_mass,fuel,size,pmix,pmiy,pmiz,csx,csy,csz,meshes,thrusters,propellants,docks,parents,children,xpdr");
    open(docks,"stock-vessel-docks.csv","tick,object,index,x,y,z,dx,dy,dz,rx,ry,rz,docked");
}
inline void snapshot(std::ofstream& state,std::ofstream& docks,unsigned tick) {
    for(unsigned index=0;index<oapiGetVesselCount();++index) {
        auto handle=oapiGetVesselByIndex(index);
        auto* vessel=oapiGetVesselInterface(handle);require(vessel!=nullptr,"Original stock vessel missing");
        VECTOR3 p{},v{},w{},pmi{},cs{};MATRIX3 r{};
        vessel->GetGlobalPos(p);vessel->GetGlobalVel(v);vessel->GetAngularVel(w);
        vessel->GetRotationMatrix(r);vessel->GetPMI(pmi);vessel->GetCrossSections(cs);
        state<<tick<<','<<oapiGetSimTime()<<','<<oapiGetSimMJD()<<','<<csv(vessel->GetName())<<','<<csv(vessel->GetClassName())
             <<','<<vessel->Version()<<','<<(handle==oapiGetFocusObject())<<','<<vessel->GetEnableFocus();
        for(double value:{p.x,p.y,p.z,v.x,v.y,v.z,r.m11,r.m12,r.m13,r.m21,r.m22,r.m23,r.m31,r.m32,r.m33,
                          w.x,w.y,w.z,vessel->GetMass(),vessel->GetEmptyMass(),vessel->GetFuelMass(),vessel->GetSize(),
                          pmi.x,pmi.y,pmi.z,cs.x,cs.y,cs.z})state<<','<<value;
        state<<','<<vessel->GetMeshCount()<<','<<vessel->GetThrusterCount()<<','<<vessel->GetPropellantCount()
             <<','<<vessel->DockCount()<<','<<vessel->AttachmentCount(true)<<','<<vessel->AttachmentCount(false)
             <<','<<(vessel->GetTransponder()!=nullptr)<<'\n';
        for(unsigned dock=0;dock<vessel->DockCount();++dock) {
            VECTOR3 pos{},dir{},rot{};auto port=vessel->GetDockHandle(dock);
            vessel->GetDockParams(port,pos,dir,rot);auto other=vessel->GetDockStatus(port);
            docks<<tick<<','<<csv(vessel->GetName())<<','<<dock;
            for(double value:{pos.x,pos.y,pos.z,dir.x,dir.y,dir.z,rot.x,rot.y,rot.z})docks<<','<<value;
            auto* peer=other?oapiGetVesselInterface(other):nullptr;
            docks<<','<<csv(peer?peer->GetName():"")<<'\n';
        }
    }
    state.flush();docks.flush();
}
}
