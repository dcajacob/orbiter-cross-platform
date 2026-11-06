// Licensed under the MIT License
// Read the actual SDK surface cache and independently reconstruct its inputs.
#pragma once
#include <cmath>
#include <ostream>
#include <stdexcept>
namespace reload_surface {
inline void Header(std::ostream& out) {
    out<<"tick,seconds,object,px,py,pz,radius,latitude_input,latitude,longitude,cached_radius,cached_latitude,cached_longitude,sin_latitude,cos_latitude,sin_longitude,cos_longitude\n";
}
inline void Rows(std::ostream& out,unsigned tick,double seconds) {
    if(!tick || tick>243)return;
    const auto earth=oapiGetObjectByName(const_cast<char*>("Earth"));
    VECTOR3 ep{};MATRIX3 er{};oapiGetGlobalPos(earth,&ep);oapiGetRotationMatrix(earth,&er);
    for(unsigned index=0;index<oapiGetVesselCount();++index) {
        const auto* vessel=oapiGetVesselInterface(oapiGetVesselByIndex(index));
        VECTOR3 position{};vessel->GetGlobalPos(position);
        const auto p=position-ep;
        const VECTOR3 q={er.m11*p.x+er.m21*p.y+er.m31*p.z,
                         er.m12*p.x+er.m22*p.y+er.m32*p.z,
                         er.m13*p.x+er.m23*p.y+er.m33*p.z};
        const double radius=std::sqrt(q.x*q.x+q.y*q.y+q.z*q.z),input=q.y/radius;
        const double latitude=std::asin(input),longitude=std::atan2(q.z,q.x);
        double cached_radius,cached_latitude,cached_longitude;
        if(vessel->GetEquPos(cached_longitude,cached_latitude,cached_radius)!=earth)
            throw std::runtime_error("Required actual Earth surface cache missing");
        out<<tick<<','<<seconds<<','<<vessel->GetName();
        for(double value:{q.x,q.y,q.z,radius,input,latitude,longitude,cached_radius,cached_latitude,cached_longitude,
                          std::sin(cached_latitude),std::cos(cached_latitude),std::sin(cached_longitude),std::cos(cached_longitude)}) {
            if(!std::isfinite(value))throw std::runtime_error("Nonfinite actual surface cache");
            out<<','<<value;
        }
        out<<'\n';
    }
    if(!out)throw std::runtime_error("Cannot write actual surface cache observation");
}
}
