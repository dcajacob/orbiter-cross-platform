// Licensed under the MIT License
#pragma once
#include <algorithm>
#include <ostream>
// Opt-in, read-only SDK samples from the same finalized step on either host.
namespace orbiter::production::playback_observation {
inline void Header(std::ostream& out) {
    out<<"tick,seconds,mjd,object,class,playback,internal,target,aperture,warp,x,y,z,vx,vy,vz,"
         "m11,m12,m13,m21,m22,m23,m31,m32,m33,wx,wy,wz,mass,fuel,main,hover,rcs,cam_dx,cam_dy,cam_dz\n";
}
inline void Row(std::ostream& out,unsigned tick) {
    auto* ship=oapiGetFocusInterface();
    VECTOR3 p{},v{},omega{},direction{};MATRIX3 rot{};
    ship->GetGlobalPos(p);ship->GetGlobalVel(v);ship->GetAngularVel(omega);ship->GetRotationMatrix(rot);
    char target[256]{};
    oapiGetObjectName(oapiCameraTarget(),target,sizeof(target));
    oapiCameraGlobalDir(&direction);
    double rcs=0;
    for(int i=THGROUP_ATT_PITCHUP;i<=THGROUP_ATT_BACK;++i)
        rcs=(std::max)(rcs,ship->GetThrusterGroupLevel(THGROUP_TYPE(i)));
    out<<tick<<','<<oapiGetSimTime()<<','<<oapiGetSimMJD()<<','<<ship->GetName()<<','<<ship->GetClassName()
       <<','<<ship->Playback()<<','<<oapiCameraInternal()<<','<<target<<','<<oapiCameraAperture()<<','<<oapiGetTimeAcceleration();
    for(double n:{p.x,p.y,p.z,v.x,v.y,v.z,rot.m11,rot.m12,rot.m13,rot.m21,rot.m22,rot.m23,rot.m31,rot.m32,rot.m33,
                  omega.x,omega.y,omega.z,ship->GetMass(),ship->GetFuelMass(),ship->GetThrusterGroupLevel(THGROUP_MAIN),
                  ship->GetThrusterGroupLevel(THGROUP_HOVER),rcs,direction.x,direction.y,direction.z})out<<','<<n;
    out<<'\n';
}
}
