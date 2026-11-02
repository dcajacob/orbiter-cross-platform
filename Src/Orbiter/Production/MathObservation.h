// Licensed under the MIT License
// Read-only engineering observations of the original SDK and elementary math.
// Include after the platform's real vessel SDK. None of these values drive physics.
#pragma once
#include <cfenv>
#include <cmath>
#include <cstdint>
#include <ostream>
#include <xmmintrin.h>
namespace orbiter::production::math_observation {
inline void Header(std::ostream& out) {
    out<<"tick,seconds,rounding,mxcsr_control,pitch,bank,heading,longitude,latitude,radius,nx,ny,nz,asin_nz,atan_nxy,rotation,sin_rotation,cos_rotation,sin_latitude,cos_latitude,sin_longitude,cos_longitude";
    for(const char* prefix:{"earth","obliquity","vessel"})for(int i=1;i<=3;++i)for(int j=1;j<=3;++j)out<<','<<prefix<<i<<j;
    out<<",ground_vx,ground_vy,ground_vz,force_x,force_y,force_z\n";
}
inline void Row(std::ostream& out,unsigned tick,double seconds,const VESSEL& vessel,
    const VECTOR3& earthPosition,const MATRIX3& earthRotation,const MATRIX3& obliquity,double rotation) {
    const auto mxcsr=_mm_getcsr()&0xffc0u;const int rounding=std::fegetround();
    MATRIX3 r{};VECTOR3 p{},ground{},force{};double longitude,latitude,radius;
    vessel.GetGlobalPos(p);vessel.GetRotationMatrix(r);vessel.GetEquPos(longitude,latitude,radius);
    vessel.GetGroundspeedVector(FRAME_LOCAL,ground);vessel.GetForceVector(force);
    p-=earthPosition;
    double nx=r.m11*p.x+r.m21*p.y+r.m31*p.z,ny=r.m12*p.x+r.m22*p.y+r.m32*p.z,nz=r.m13*p.x+r.m23*p.y+r.m33*p.z;
    const double inverse=1./std::sqrt(nx*nx+ny*ny+nz*nz);nx*=inverse;ny*=inverse;nz*=inverse;
    out<<tick<<','<<seconds<<','<<rounding<<','<<mxcsr<<','<<vessel.GetPitch()<<','<<vessel.GetBank()<<','<<vessel.GetYaw()
        <<','<<longitude<<','<<latitude<<','<<radius<<','<<nx<<','<<ny<<','<<nz<<','<<std::asin(nz)<<','<<std::atan2(nx,ny)
        <<','<<rotation<<','<<std::sin(rotation)<<','<<std::cos(rotation)<<','<<std::sin(latitude)<<','<<std::cos(latitude)
        <<','<<std::sin(longitude)<<','<<std::cos(longitude);
    const MATRIX3* matrices[]={&earthRotation,&obliquity,&r};
    for(const auto* matrix:matrices)for(double value:matrix->data)out<<','<<value;
    out<<','<<ground.x<<','<<ground.y<<','<<ground.z<<','<<force.x<<','<<force.y<<','<<force.z<<'\n';
}
}
