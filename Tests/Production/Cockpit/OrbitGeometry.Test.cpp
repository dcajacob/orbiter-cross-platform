// Licensed under the MIT License
// Independent conic/rotation checks on the production MFD's original plotting code.
#include "MfdOrbitGeometry.h"
#include <array>
#include <cmath>
#include <iostream>
#include <limits>
#include <stdexcept>

namespace {
void require(bool value,const char* message) {if(!value) throw std::runtime_error(message);}
void orthogonal(const Matrix& rotation) {
    const auto product=rotation*transp(rotation);
    for(int row=0;row<3;++row) for(int column=0;column<3;++column)
        require(std::abs(product(row,column)-(row==column?1.:0.))<2e-14,"MFD projection matrix is not orthogonal");
}
void conic(double eccentricity,double inclination,bool orbital_plane) {
    constexpr double epoch=51544.5;
    const double major=eccentricity<1?7e6:-7e6;
    Elements elements(major,eccentricity,inclination,.7,1.1,1.2,epoch,epoch);
    elements.Setup(1000,5.972e24,epoch,epoch);
    Vector position,velocity;elements.Update(position,velocity,123.);
    auto rotation=RotMatrix(elements.coso,elements.sino,elements.cost,elements.sint,elements.cosi,elements.sini);
    auto projection=orbital_plane?IRotMatrix(elements.cost,elements.sint,elements.cosi,elements.sini):IMatrix();
    orthogonal(rotation);orthogonal(projection);
    rotation.premul(projection);
    constexpr int center=256;constexpr double scale=1e-5;
    std::array<oapi::IVECTOR2,ELN+7> points;
    for(auto& point:points) {point.x=0x12345;point.y=-0x12345;}
    UpdateOrbitGraph(center,center,512,512,scale,&elements,rotation,projection,points.data()+1);
    require(points.front().x==0x12345 && points.back().x==0x12345,"MFD conic wrote outside its output array");
    const auto* p=points.data()+1;
    const int count=eccentricity<1?ELN:ELN-1;
    const auto inverse=transp(rotation);
    // In the orbital plane, invert the plotted (integer pixel) projection and
    // check the conic equation. Pixel truncation gives a bounded distance error.
    if(orbital_plane) for(int index=0;index<count;++index) {
        const auto point=mul(inverse,Vector((p[index].x-center)/scale,0,(center-p[index].y)/scale));
        const double focus_distance=std::hypot(point.x,point.z);
        const double polar_parameter=major*(1-eccentricity*eccentricity);
        require(std::abs(focus_distance+eccentricity*point.x-polar_parameter)<(1+eccentricity)*1.42/scale,
            "MFD polygon does not follow the analytical conic within pixel rounding");
    }
    const auto projected=mul(projection,position);
    require(p[ELN].x==center+int(projected.x*scale) && p[ELN].y==center-int(projected.z*scale),
        "MFD radius marker uses the wrong coordinates or vertical direction");
    if(eccentricity>=1) require(p[ELN+2].x==-1,"Hyperbolic MFD must mark apoapsis invalid");
    else if(orbital_plane) {
        const auto periapsis=mul(rotation,Vector(elements.PeDist(),0,0));
        const auto apoapsis=mul(rotation,Vector(-major*(1+eccentricity),0,0));
        require(std::abs(p[ELN+1].x-(center+periapsis.x*scale))<2 && std::abs(p[ELN+1].y-(center-periapsis.z*scale))<2,
            "MFD periapsis marker differs from analytical periapsis");
        require(std::abs(p[ELN+2].x-(center+apoapsis.x*scale))<2 && std::abs(p[ELN+2].y-(center-apoapsis.z*scale))<2,
            "MFD apoapsis marker differs from analytical apoapsis");
    }
    if(eccentricity>=1) for(const double invalid:{0.,std::numeric_limits<double>::quiet_NaN()}) {
        for(auto& point:points) {point.x=45;point.y=67;}
        UpdateOrbitGraph(center,center,512,512,invalid,&elements,rotation,projection,points.data()+1);
        for(const auto& point:points) require(point.x==45 && point.y==67,"Invalid hyperbolic scale changed output");
    }
}
}
int main() {
    try {
        for(const double eccentricity:{0.,.3,.9,1.2,2.})
            for(const double inclination:{.0,.7,1.5,2.4})
                for(const bool orbital_plane:{false,true}) conic(eccentricity,inclination,orbital_plane);
        oapi::IVECTOR2 point;MapScreen(100,200,2,Vector(-1.75,999,3.25),&point);
        require(point.x==97 && point.y==194,"MFD mapping changed truncation or coordinate conventions");
        require(PointInView(512,512,&point),"MFD visible point rejected");
        point.x=512;require(!PointInView(512,512,&point),"MFD right edge must be excluded");
        std::cout<<"Original MFD conics: 40 circular/eccentric/hyperbolic/inclined projections, analytical pixel bounds and invalid scales pass\n";
    } catch(const std::exception& error) {std::cerr<<error.what()<<'\n';return 1;}
}
