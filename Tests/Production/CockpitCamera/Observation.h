// Licensed under the MIT License
// Public SDK fixture controls and read-only camera/physical observations.
#pragma once
#include <cmath>
#include <fstream>
#include <iomanip>
#include <locale>
#include <stdexcept>

namespace camera_fixture {
inline void require(bool ok,const char* message) {
    if(!ok)throw std::runtime_error(message);
}
inline void Apply() {
    double phi=0,theta=0;int reopen=0;
    std::ifstream input("headlook.txt");
    require(bool(input>>phi>>theta>>reopen) && std::isfinite(phi) && std::isfinite(theta) &&
            (reopen==0 || reopen==1),"Invalid public SDK headlook fixture");
    oapiCameraSetCockpitDir(phi,theta,false);
    if(reopen) {
        oapiOpenMFD(2,0);oapiOpenMFD(1,0);
        oapiOpenMFD(1,1);oapiOpenMFD(2,1);
    }
    std::ofstream("camera-inputs.csv")<<std::setprecision(17)
        <<"tick,phi,theta,reopen\n0,"<<phi<<','<<theta<<','<<reopen<<'\n';
}
inline void Open(std::ofstream& stream,const char* path,const char* header) {
    stream.imbue(std::locale::classic());
    stream.exceptions(std::ios::badbit|std::ios::failbit);
    stream.open(path);stream<<std::setprecision(17)<<header<<'\n';
}
inline void CameraHeader(std::ofstream& stream) {
    Open(stream,"camera-sdk.csv","tick,seconds,internal,cockpit,aperture,x,y,z,m11,m12,m13,m21,m22,m23,m31,m32,m33");
}
inline void Camera(std::ofstream& stream,unsigned tick) {
    auto* vessel=oapiGetFocusInterface();require(vessel!=nullptr,"Headlook focus missing");
    VECTOR3 position{},origin{};MATRIX3 rotation{},body{};
    oapiCameraGlobalPos(&position);oapiCameraRotationMatrix(&rotation);
    vessel->GetGlobalPos(origin);vessel->GetRotationMatrix(body);
    const VECTOR3 local=tmul(body,position-origin);
    const MATRIX3 relative=mul(transp(body),rotation);
    stream<<tick<<','<<oapiGetSimTime()<<','<<oapiCameraInternal()
        <<','<<oapiCockpitMode()<<','<<oapiCameraAperture();
    for(double value:{local.x,local.y,local.z,relative.m11,relative.m12,relative.m13,
                     relative.m21,relative.m22,relative.m23,relative.m31,relative.m32,relative.m33})stream<<','<<value;
    stream<<'\n';stream.flush();
}
inline void StateHeader(std::ofstream& stream) {
    Open(stream,"cockpit-state.csv","tick,seconds,mjd,object,class,cockpit,hud,left_mfd,right_mfd,x,y,z,vx,vy,vz,m11,m12,m13,m21,m22,m23,m31,m32,m33,wx,wy,wz,mass,fuel,meshes,thrusters");
}
inline void State(std::ofstream& stream,unsigned tick) {
    auto* vessel=oapiGetFocusInterface();require(vessel!=nullptr,"Headlook vessel missing");
    VECTOR3 p{},v{},w{};MATRIX3 r{};
    vessel->GetGlobalPos(p);vessel->GetGlobalVel(v);vessel->GetAngularVel(w);vessel->GetRotationMatrix(r);
    stream<<tick<<','<<oapiGetSimTime()<<','<<oapiGetSimMJD()<<','<<vessel->GetName()<<','<<vessel->GetClassName()
        <<','<<oapiCockpitMode()<<','<<oapiGetHUDMode()<<','<<oapiGetMFDMode(0)<<','<<oapiGetMFDMode(1);
    for(double value:{p.x,p.y,p.z,v.x,v.y,v.z,r.m11,r.m12,r.m13,r.m21,r.m22,r.m23,r.m31,r.m32,r.m33,
                     w.x,w.y,w.z,vessel->GetMass(),vessel->GetFuelMass()})stream<<','<<value;
    stream<<','<<vessel->GetMeshCount()<<','<<vessel->GetThrusterCount()<<'\n';stream.flush();
}
}
