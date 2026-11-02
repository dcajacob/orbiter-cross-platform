// Licensed under the MIT License
#pragma once
#include <string>
namespace production_test {
inline bool GroundFlightCase(const std::string& id) {
    return id=="pb_ground_idle" || id=="pb_atmosphere" || id=="pb_contact" ||
        id=="pb_takeoff_landing" || id=="pb_ground_persistence" || id=="pb_ground_reload";
}
// Control/setup commands only. Every force and contact comes from the stock SDK.
inline void GroundFlightStart(VESSEL* v,const std::string& id) {
    if(id!="pb_atmosphere" && id!="pb_contact")return;
    VESSELSTATUS2 status{};status.version=2;v->GetStatusEx(&status);
    VECTOR3 p{},ep{};oapiGetGlobalPos(status.rbody,&ep);v->GetGlobalPos(p);status.rpos=p-ep;
    const double radius=length(status.rpos);
    status.rpos*=1+(id=="pb_atmosphere"?1500.:8.)/radius;
    MATRIX3 r{};v->GetRotationMatrix(r);
    v->GetGlobalOrientation(status.arot);v->GetAngularVel(status.vrot);
    if(id=="pb_atmosphere")status.rvel+=mul(r,_V(0,0,200));
    else status.rvel-=status.rpos*(.5/length(status.rpos));
    status.status=0;status.flag=0;v->DefSetStateEx(&status);
}
inline void GroundFlight(VESSEL* v,const std::string& id,unsigned tick) {
    if(id=="pb_atmosphere") {
        if(tick==0)v->ActivateNavmode(NAVMODE_HLEVEL);
        v->SetThrusterGroupLevel(THGROUP_MAIN,.15);
    } else if(id=="pb_takeoff_landing") {
        if(tick==0)v->ActivateNavmode(NAVMODE_HLEVEL);
        // Four seconds lifting, five decelerating, then a powered descent.
        v->SetThrusterGroupLevel(THGROUP_HOVER,tick<80?1.:tick<180?.65:tick<700?.78:0.);
    }
}
}
