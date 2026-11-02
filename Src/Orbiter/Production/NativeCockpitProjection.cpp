// Copyright (c) Martin Schweiger
// Licensed under the MIT License
// The original CameraApplication/D3dmath float stages, without device types.
#include "CockpitProjection.h"
#include "Camera.h"
#include <cmath>
namespace orbiter::production {
bool ProjectCockpitDirection(const Camera& camera,const Vector& direction,CockpitPoint& result)
{
    const auto p=camera.ProjectionMatrix(),v=camera.ViewMatrix();
    float projection[16]={},view[16]={},product[16]={};
    projection[0]=float(p.m11);projection[5]=float(p.m22);
    if(camera.Farplane()>=1e20) {
        projection[10]=1.f;projection[14]=-camera.Nearplane();
    } else {
        projection[14]=(projection[10]=camera.Farplane()/(camera.Farplane()-camera.Nearplane()))*(-camera.Nearplane());
    }
    projection[11]=1.f;
    view[0]=float(v.m11);view[1]=float(v.m12);view[2]=float(v.m13);
    view[4]=float(v.m21);view[5]=float(v.m22);view[6]=float(v.m23);
    view[8]=float(v.m31);view[9]=float(v.m32);view[10]=float(v.m33);view[15]=1.f;
    for(unsigned i=0;i<4;i++)
        for(unsigned j=0;j<4;j++)
            for(unsigned k=0;k<4;k++)
                product[4*i+j]+=projection[4*k+j]*view[4*i+k];
    const CockpitPoint source{float(direction.x),float(direction.y),float(direction.z)};
    const float x=source.x*product[0]+source.y*product[4]+source.z*product[8]+product[12];
    const float y=source.x*product[1]+source.y*product[5]+source.z*product[9]+product[13];
    const float z=source.x*product[2]+source.y*product[6]+source.z*product[10]+product[14];
    const float w=source.x*product[3]+source.y*product[7]+source.z*product[11]+product[15];
    if(std::fabs(w)<1.e-5f)return false;
    result={x/w,y/w,z/w};
    return result.x>=-1.f && result.x<=1.f && result.y>=-1.f && result.y<=1.f && result.z<=camera.HomogZlimit();
}
}
