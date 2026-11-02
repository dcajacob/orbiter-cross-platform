// Licensed under the MIT License
// Engineering observation only. Include after the matching internal Vessel.h.
// Windows diagnostics compile against the verified frozen application's headers;
// native diagnostics use their own build's headers. No SDK ABI is introduced.
#pragma once
#include <ostream>
#include <stdexcept>
namespace orbiter::production::contact_observation {
// Explicit instantiation permits naming private members without changing the
// class declaration or layout. These accessors only read existing force caches.
template<class Tag,typename Tag::Type Member> struct Access {
    friend typename Tag::Type Read(Tag) {return Member;}
};
struct Count {using Type=int Vessel::*;friend Type Read(Count);};
struct Capacity {using Type=int Vessel::*;friend Type Read(Capacity);};
struct Forces {using Type=Vector* Vessel::*;friend Type Read(Forces);};
struct Positions {using Type=Vector* Vessel::*;friend Type Read(Positions);};
struct Touchdown {using Type=TOUCHDOWN_VTX* Vessel::*;friend Type Read(Touchdown);};
template struct Access<Count,&Vessel::nforcevec>;
template struct Access<Capacity,&Vessel::forcevecbuf>;
template struct Access<Forces,&Vessel::forcevec>;
template struct Access<Positions,&Vessel::forcepos>;
template struct Access<Touchdown,&Vessel::touchdown_vtx>;
inline void Header(std::ostream& out) {
    out<<"tick,seconds,force_count";
    for(unsigned i=0;i<3;++i)for(const char* field:{"compression","mu","mu_lng"})out<<",touchdown"<<i<<'_'<<field;
    for(unsigned i=0;i<10;++i)for(const char* field:{"present","fx","fy","fz","px","py","pz"})out<<",reaction"<<i<<'_'<<field;
    out<<'\n';
}
inline void Row(std::ostream& out,unsigned tick,double seconds,const VESSEL& sdk) {
    auto* core=static_cast<Vessel*>(sdk.GetHandle());
    if(!core || core->GetModuleInterface()!=&sdk || sdk.GetTouchdownPointCount()!=12)
        throw std::runtime_error("Internal contact observer requires the matching real ShuttlePB object");
    const int count=core->*Read(Count{}),capacity=core->*Read(Capacity{});
    const auto* forces=core->*Read(Forces{});const auto* positions=core->*Read(Positions{});
    const auto* points=core->*Read(Touchdown{});
    if(capacity!=10 || count<0 || count>capacity || !forces || !positions || !points)
        throw std::runtime_error("Internal contact observer layout/capacity check failed");
    // Check the internal record against independently exported SDK fields before
    // observing the internal compression/friction fields absent from that SDK.
    for(unsigned i=0;i<3;++i) {
        TOUCHDOWNVTX point{};
        if(!sdk.GetTouchdownPoint(point,i) || point.pos.x!=points[i].pos.x || point.pos.y!=points[i].pos.y || point.pos.z!=points[i].pos.z ||
            point.stiffness!=points[i].stiffness || point.damping!=points[i].damping)
            throw std::runtime_error("Internal contact observer touchdown layout check failed");
    }
    out<<tick<<','<<seconds<<','<<count;
    for(unsigned i=0;i<3;++i)out<<','<<points[i].compression<<','<<points[i].mu<<','<<points[i].mu_lng;
    for(int i=0;i<10;++i) {
        if(i<count)out<<",1,"<<forces[i].x<<','<<forces[i].y<<','<<forces[i].z<<','<<positions[i].x<<','<<positions[i].y<<','<<positions[i].z;
        else out<<",0,0,0,0,0,0,0";
    }
    out<<'\n';
}
}
