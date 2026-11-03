// Licensed under the MIT License
#pragma once
#include "FlightInput.h"
#include <algorithm>
#include <cmath>

namespace orbiter::production {
// -2 selects the conventional Z/slider positions from Orbiter.cfg. Explicit
// GLFW axis assignments (UI or CLI) use zero-based indices, with -1 disabled.
inline int NativeThrottleAxis(unsigned setting,int overrideAxis) {
    if(overrideAxis!=-2)return overrideAxis;
    return setting==1 ? 2 : setting==2 ? 6 : setting==3 ? 7 : -1;
}

inline int NativeJoystickAxis(float value,int deadzone) {
    if(!std::isfinite(value))return 0;
    double dead=std::clamp(deadzone,0,10000)/10000.;
    double magnitude=std::min(1.,std::abs(double(value)));
    if(magnitude<=dead)return 0;
    return int(std::lround(std::copysign((magnitude-dead)/(1.-dead)*1000.,value)));
}

class NativeJoystickState {
    int device_=-1,axis_=-1,previous_=1;
    bool initialized_=false,ignore_=false;
public:
    void Reset() {device_=-1;axis_=-1;previous_=1;initialized_=false;ignore_=false;}
    void Poll(int device,const float* axes,int count,int rudder,int throttle,
              int deadzone,int saturation,bool ignoreOnStart,FlightInput& input) {
        if(device!=device_ || throttle!=axis_) {
            Reset();device_=device;axis_=throttle;
        }
        if(device<0 || !axes)return;
        auto axis=[&](int i) {return i>=0 && i<count ? NativeJoystickAxis(axes[i],deadzone) : 0;};
        input.x=axis(0);input.y=axis(1);input.rz=axis(rudder);
        if(throttle<0 || throttle>=count || !std::isfinite(axes[throttle]))return;
        double limit=std::clamp(saturation,0,10000)/10000.;
        double raw=axes[throttle];
        double value=limit>0 ? std::clamp(raw/limit,-1.,1.) : raw<0 ? -1. : raw>0 ? 1. : 0.;
        // Original DirectInput throttle range [-1000,0] and eight-count bins.
        // floor reproduces the original signed right shift without depending
        // on implementation-defined negative integer shifts.
        int quantized=int(std::floor(std::lround((value-1.)*500.)/8.));
        if(!initialized_) {
            initialized_=true;ignore_=ignoreOnStart;
            if(ignore_)previous_=quantized;
        }
        if(quantized==previous_)return;
        if(ignore_) {
            if(std::abs(quantized-previous_)<=10)return;
            ignore_=false;
        }
        previous_=quantized;
        input.throttle=std::min(1.,-0.008*quantized);
    }
};
}
