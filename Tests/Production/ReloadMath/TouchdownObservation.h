// Licensed under the MIT License
// Passive SDK reads and a separate reconstruction of original touchdown-coordinate math.
// These values never enter the simulation. The caller must prove baseline equivalence.
#pragma once
#include <cmath>
#include <ostream>
#include <stdexcept>
namespace reload_touchdown {
inline void Header(std::ostream& out) {
    out << "tick,seconds,object,point,point_count,px,py,pz,earth_x,earth_y,earth_z,ship_x,ship_y,ship_z,vertex_x,vertex_y,vertex_z,radius,latitude_input,latitude,longitude,sin_latitude,cos_latitude,sin_longitude,cos_longitude\n";
}
inline void Rows(std::ostream& out,unsigned tick,double seconds) {
    if(tick>243)return;
    auto earth=oapiGetObjectByName(const_cast<char*>("Earth"));
    if(!earth)throw std::runtime_error("Required Earth missing in passive touchdown observation");
    VECTOR3 ep{};MATRIX3 er{};oapiGetGlobalPos(earth,&ep);oapiGetRotationMatrix(earth,&er);
    for(unsigned index=0;index<oapiGetVesselCount();++index) {
        auto* vessel=oapiGetVesselInterface(oapiGetVesselByIndex(index));
        if(!vessel)throw std::runtime_error("Required actual vessel missing");
        VECTOR3 p{};MATRIX3 r{},t{};vessel->GetGlobalPos(p);vessel->GetRotationMatrix(r);
        VECTOR3 relative={p.x-ep.x,p.y-ep.y,p.z-ep.z};
        VECTOR3 shift={er.m11*relative.x+er.m21*relative.y+er.m31*relative.z,
                       er.m12*relative.x+er.m22*relative.y+er.m32*relative.z,
                       er.m13*relative.x+er.m23*relative.y+er.m33*relative.z};
        // Same left-to-right scalar order as Matrix::tpremul in Vecmat.cpp.
        for(unsigned i=0;i<3;++i)for(unsigned j=0;j<3;++j)
            t.data[i*3+j]=er.data[i]*r.data[j]+er.data[3+i]*r.data[3+j]+er.data[6+i]*r.data[6+j];
        const unsigned count=vessel->GetTouchdownPointCount();
        for(unsigned point=0;point<count;++point) {
            TOUCHDOWNVTX vertex{};
            if(!vessel->GetTouchdownPoint(vertex,point))throw std::runtime_error("Actual touchdown point missing");
            const auto& v=vertex.pos;
            VECTOR3 q={t.m11*v.x+t.m12*v.y+t.m13*v.z+shift.x,
                       t.m21*v.x+t.m22*v.y+t.m23*v.z+shift.y,
                       t.m31*v.x+t.m32*v.y+t.m33*v.z+shift.z};
            const double radius=std::sqrt(q.x*q.x+q.y*q.y+q.z*q.z);
            const double input=q.y/radius,latitude=std::asin(input),longitude=std::atan2(q.z,q.x);
            out<<tick<<','<<seconds<<','<<vessel->GetName()<<','<<point<<','<<count;
            for(double value:{q.x,q.y,q.z,ep.x,ep.y,ep.z,p.x,p.y,p.z,v.x,v.y,v.z,radius,input,latitude,longitude,
                              std::sin(latitude),std::cos(latitude),std::sin(longitude),std::cos(longitude)}) {
                if(!std::isfinite(value))throw std::runtime_error("Nonfinite passive touchdown value");
                out<<','<<value;
            }
            out<<'\n';
        }
    }
    if(!out)throw std::runtime_error("Cannot write passive touchdown observation");
}
}
