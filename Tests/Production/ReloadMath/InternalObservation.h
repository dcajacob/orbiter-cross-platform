// Licensed under the MIT License
// Read existing state through the exact owning runtime's internal headers.
// Public SDK position/matrix fences must pass before internal observations are used.
#pragma once
#include "Vessel.h"
#include "SuperVessel.h"
#include <cmath>
#include <ostream>
#include <stdexcept>
namespace reload_internal {
inline void Header(std::ostream& out) {
    out<<"tick,seconds,object,kind";
    for(const char* side:{"current","other"}) {
        for(const char* field:{"x","y","z","vx","vy","vz","wx","wy","wz","qx","qy","qz","qs"})out<<','<<side<<'_'<<field;
        for(unsigned i=0;i<9;++i)out<<','<<side<<"_r"<<i;
    }
    out<<",gravity_update,gravity_count,gravity_candidate,gravity0,gravity1,gravity2,gravity3\n";
}
inline void BodyRow(std::ostream& out,unsigned tick,double seconds,const char* name,const char* kind,const RigidBody& body) {
    if(!body.s0 || !body.s1)throw std::runtime_error("Required actual internal state missing");
    out<<tick<<','<<seconds<<','<<name<<','<<kind;
    for(const auto* state:{body.s0,body.s1}) {
        for(double value:{state->pos.x,state->pos.y,state->pos.z,state->vel.x,state->vel.y,state->vel.z,
                          state->omega.x,state->omega.y,state->omega.z,state->Q.qvx,state->Q.qvy,state->Q.qvz,state->Q.qs}) {
            if(!std::isfinite(value))throw std::runtime_error("Nonfinite internal state observation");
            out<<','<<value;
        }
        for(double value:state->R.data)out<<','<<value;
    }
    const auto& g=body.GetGFieldData();
    if(!std::isfinite(g.updt) || g.ngrav<0 || g.ngrav>100)throw std::runtime_error("Invalid internal gravity-cache layout");
    out<<','<<g.updt<<','<<g.ngrav<<','<<g.testidx;
    for(unsigned i=0;i<4;++i)out<<','<<(g.ngrav>i?g.gravidx[i]:-1);
    out<<'\n';
}
inline void Rows(std::ostream& out,unsigned tick,double seconds) {
    if(tick==0 || tick>243)return;
    for(unsigned index=0;index<oapiGetVesselCount();++index) {
        const auto handle=oapiGetVesselByIndex(index);auto* sdk=oapiGetVesselInterface(handle);
        auto* core=static_cast<const Vessel*>(handle);
        VECTOR3 p{},v{};MATRIX3 r{};sdk->GetGlobalPos(p);sdk->GetGlobalVel(v);sdk->GetRotationMatrix(r);
        if(!core || !core->s0 || p.x!=core->s0->pos.x || p.y!=core->s0->pos.y || p.z!=core->s0->pos.z ||
           v.x!=core->s0->vel.x || v.y!=core->s0->vel.y || v.z!=core->s0->vel.z)
            throw std::runtime_error("Public/internal position ABI fence failed");
        for(unsigned i=0;i<9;++i)if(r.data[i]!=core->s0->R.data[i])throw std::runtime_error("Public/internal matrix ABI fence failed");
        BodyRow(out,tick,seconds,sdk->GetName(),"vessel",*core);
        if(const auto* aggregate=core->SuperStruct())BodyRow(out,tick,seconds,sdk->GetName(),"aggregate",*aggregate);
    }
    if(!out)throw std::runtime_error("Cannot write internal state observation");
}
}
