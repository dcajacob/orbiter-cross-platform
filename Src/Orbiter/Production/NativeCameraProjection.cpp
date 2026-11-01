// Licensed under the MIT License
#include "Camera.h"
#include <cmath>
// The OpenGL client builds its GPU projection from Camera's original values.
bool Camera::Direction2Viewport(const Vector& dir,int& x,int& y)
{
    const Vector view=tmul(grot,dir);
    if(view.z==0) return false;
    const double hx=view.x*(aspect/tan_ap)/view.z;
    const double hy=view.y/tan_ap/view.z;
    const double hz=farplane/(farplane-nearplane)*(1.0-nearplane/view.z);
    if(hx>=-1.0 && hy<=1.0 && hz<=1.0) {
        if(std::hypot(hx,hy)<1e-6) {x=int(w05);y=int(h05);}
        else {x=int(w05*(1.0+hx));y=int(h05*(1.0-hy));}
        return true;
    }
    return false;
}
