// Licensed under the MIT License
#pragma once
#include "FlightInput.h"
#include <algorithm>
#include <cmath>
#include <string_view>

namespace orbiter::production {
// -2 selects the conventional Z/slider positions from Orbiter.cfg. Explicit
// GLFW axis assignments (UI or CLI) use zero-based indices, with -1 disabled.
inline int NativeThrottleAxis(unsigned setting,int overrideAxis) {
    if(overrideAxis!=-2)return overrideAxis;
    return setting==1 ? 2 : setting==2 ? 6 : setting==3 ? 7 : -1;
}

inline bool NativeJoystickAlternate(const unsigned char* buttons, int count, std::string_view guid) {
    // The VelocityOne Flightstick in PC mode reports its base X button as
    // GLFW button 7. Match the Linux USB GUID through the product ID so a
    // firmware revision does not change the binding.
    constexpr std::string_view velocityOnePc = "03000000f510000055700000";
    const int button = guid.substr(0, velocityOnePc.size()) == velocityOnePc ? 6 : 2;
    return buttons && count > button && buttons[button] != 0;
}

inline int NativeJoystickAxis(float value,int deadzone) {
    if(!std::isfinite(value))return 0;
    double dead=std::clamp(deadzone,0,10000)/10000.;
    double magnitude=std::min(1.,std::abs(double(value)));
    if(magnitude<=dead)return 0;
    return int(std::lround(std::copysign((magnitude-dead)/(1.-dead)*1000.,value)));
}

class NativeJoystickState {
    int device_=-1,rudder_=-1,axis_=-1,previous_=1;
    bool attitudeReady_=false;
    bool initialized_=false,ignore_=false,inverted_=false;
public:
    void Reset() { *this = NativeJoystickState{}; }
    void DeviceChanged(int device) { if (device == device_) Reset(); }
    void Poll(int device,const float* axes,int count,int rudder,int throttle,
              int deadzone,int saturation,bool ignoreOnStart,FlightInput& input,bool invertThrottle=false) {
        if (device != device_) {
            Reset();
            device_ = device;
        }
        if (rudder != rudder_) {
            rudder_ = rudder;
            attitudeReady_ = false;
        }
        if (throttle != axis_ || invertThrottle != inverted_) {
            axis_ = throttle;
            inverted_ = invertThrottle;
            previous_ = 1;
            initialized_ = false;
            ignore_ = false;
        }
        if(device<0 || !axes)return;
        const auto available = [&](int index) { return index >= 0 && index < count; };
        const auto axis = [&](int index) { return available(index) ? NativeJoystickAxis(axes[index],deadzone) : 0; };
        const auto neutral = [&](int index) {
            return !available(index) || (std::isfinite(axes[index]) && axis(index) == 0);
        };
        // Some devices report endpoint values before sending their first centered
        // sample. Keep them from firing attitude thrusters on connection.
        attitudeReady_ = attitudeReady_ || (count > 0 && neutral(0) && neutral(1) && neutral(rudder));
        if (attitudeReady_) {
            input.x = axis(0);
            input.y = axis(1);
            input.rz = axis(rudder);
        }
        if(throttle<0 || throttle>=count || !std::isfinite(axes[throttle]))return;
        double limit=std::clamp(saturation,0,10000)/10000.;
        double raw=invertThrottle ? -axes[throttle] : axes[throttle];
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
