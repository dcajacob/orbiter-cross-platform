// Licensed under the MIT License
// Read-only engineering observations of the original SDK and elementary math.
// Include after the platform's real vessel SDK. None of these values drive physics.
#pragma once
#include <cfenv>
#include <cmath>
#include <cstdint>
#include <ostream>
#include <stdexcept>
#include <xmmintrin.h>
namespace orbiter::production::math_observation {
inline void Header(std::ostream& out) {
    out<<"tick,seconds,rounding,mxcsr_control,pitch,bank,heading,longitude,latitude,radius,nx,ny,nz,asin_nz,atan_nxy,rotation,sin_rotation,cos_rotation,sin_latitude,cos_latitude,sin_longitude,cos_longitude";
    for(const char* prefix:{"earth","obliquity","vessel"})for(int i=1;i<=3;++i)for(int j=1;j<=3;++j)out<<','<<prefix<<i<<j;
    out<<",ground_vx,ground_vy,ground_vz,force_x,force_y,force_z,elevation,normal_x,normal_y,normal_z,angular_ax,angular_ay,angular_az,thrust_x,thrust_y,thrust_z,lift_x,lift_y,lift_z,drag_x,drag_y,drag_z,pmi_x,pmi_y,pmi_z";
    for(unsigned point=0;point<3;++point)for(const char* field:{"x","y","z","stiffness","damping","mu","mu_lng"})out<<",touchdown"<<point<<'_'<<field;
    out<<'\n';
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
    VECTOR3 a{},thrust{},lift{},drag{},pmi{};const auto normal=vessel.GetSurfaceNormal();
    vessel.GetAngularAcc(a);vessel.GetThrustVector(thrust);vessel.GetLiftVector(lift);vessel.GetDragVector(drag);vessel.GetPMI(pmi);
    out<<','<<ground.x<<','<<ground.y<<','<<ground.z<<','<<force.x<<','<<force.y<<','<<force.z<<','<<vessel.GetSurfaceElevation();
    for(const auto& value:{normal,a,thrust,lift,drag,pmi})out<<','<<value.x<<','<<value.y<<','<<value.z;
    for(unsigned point=0;point<3;++point) {
        TOUCHDOWNVTX vertex{};if(!vessel.GetTouchdownPoint(vertex,point))throw std::runtime_error("Required stock touchdown point missing");
        out<<','<<vertex.pos.x<<','<<vertex.pos.y<<','<<vertex.pos.z<<','<<vertex.stiffness<<','<<vertex.damping<<','<<vertex.mu<<','<<vertex.mu_lng;
    }
    out<<'\n';
}
}
