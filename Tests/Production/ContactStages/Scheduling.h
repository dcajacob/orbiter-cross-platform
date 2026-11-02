// Licensed under the MIT License
// Read-only diagnostic. Include after this build's matching internal Vessel.h.
#pragma once
#include <ostream>
#include <stdexcept>
namespace contact_scheduling {
template<class Tag,typename Tag::Type Member>struct Access {friend typename Tag::Type Read(Tag){return Member;}};
struct Counter {using Type=int Body::*;friend Type Read(Counter);};
struct PositionBase {using Type=Vector Body::*;friend Type Read(PositionBase);};
struct PositionAdd {using Type=Vector Body::*;friend Type Read(PositionAdd);};
struct VelocityBase {using Type=Vector Body::*;friend Type Read(VelocityBase);};
struct VelocityAdd {using Type=Vector Body::*;friend Type Read(VelocityAdd);};
template struct Access<Counter,&Body::updcount>;
template struct Access<PositionBase,&Body::rpos_base>;
template struct Access<PositionAdd,&Body::rpos_add>;
template struct Access<VelocityBase,&Body::rvel_base>;
template struct Access<VelocityAdd,&Body::rvel_add>;
inline int IncrementCounter(const Body& body){return body.*Read(Counter{});}
inline void Header(std::ostream& out) {
    out<<"tick,seconds,object,increment_counter,gravity_update,gravity_source_count,gravity_next_candidate";
    for(const char* prefix:{"position_base","position_add","velocity_base","velocity_add"})
        for(const char* axis:{"x","y","z"})out<<','<<prefix<<'_'<<axis;
    out<<'\n';
}
inline void Row(std::ostream& out,unsigned tick,double seconds,const VESSEL& sdk) {
    auto* core=static_cast<Vessel*>(sdk.GetHandle());
    if(!core || core->GetModuleInterface()!=&sdk)throw std::runtime_error("Scheduling observer requires matching production headers");
    const auto& field=core->GetGFieldData();const int count=IncrementCounter(*core);
    if(count<0 || count>1000 || field.ngrav>MAXGFIELDLIST)throw std::runtime_error("Invalid scheduling observer layout/state");
    out<<tick<<','<<seconds<<','<<core->Name()<<','<<count<<','<<field.updt<<','<<field.ngrav<<','<<field.testidx;
    for(const auto& v:{core->*Read(PositionBase{}),core->*Read(PositionAdd{}),core->*Read(VelocityBase{}),core->*Read(VelocityAdd{})})
        out<<','<<v.x<<','<<v.y<<','<<v.z;
    out<<'\n';
}
}
