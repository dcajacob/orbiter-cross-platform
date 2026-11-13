// Licensed under the MIT License
#include "Production/NativeJoystick.h"
#include <limits>
#include <stdexcept>
#include <iostream>
using namespace orbiter::production;
namespace {
void require(bool condition,const char* message) {if(!condition)throw std::runtime_error(message);}
}
int main() {
    try {
        require(NativeJoystickAxis(.25f,2500)==0,"Deadzone edge must remain neutral");
        require(NativeJoystickAxis(.5f,2500)==333,"Remaining travel must span the calibrated range");
        require(NativeJoystickAxis(-1,2500)==-1000 && NativeJoystickAxis(1,2500)==1000,"Both axis endpoints must retain full authority");
        require(NativeJoystickAxis(1,10000)==0,"A full deadzone must disable the axis");
        require(NativeJoystickAxis(std::numeric_limits<float>::quiet_NaN(),0)==0,"Invalid device data must not reach flight controls");
        require(NativeThrottleAxis(1,-2)==2 && NativeThrottleAxis(2,-2)==6 && NativeThrottleAxis(3,-2)==7,"Legacy throttle selections changed");
        require(NativeThrottleAxis(0,-2)==-1 && NativeThrottleAxis(1,3)==3,"Keyboard-only or explicit raw axis assignment changed");
        NativeJoystickState state;
        float axes[]={.5f,-.5f,0,0};
        auto poll=[&](int device=0,int throttle=3,bool ignore=true,int saturation=9500,bool invert=false) {
            FlightInput input;
            state.Poll(device,axes,4,2,throttle,2500,saturation,ignore,input,invert);
            return input;
        };
        auto input=poll();
        require(input.x==333 && input.y==-333 && input.rz==0,"Calibrated controls did not reach FlightInput");
        require(input.throttle<0,"Initial throttle must be ignored");
        axes[3]=.05f;require(poll().throttle<0,"Throttle noise must not arm the engine");
        axes[3]=-.95f;require(poll().throttle==1,"Throttle travel must arm and saturate at full thrust");
        require(poll().throttle<0,"An unmoved throttle must not override keyboard control");
        axes[3]=.95f;require(poll().throttle==0,"Opposite throttle endpoint must stop thrust");
        require(poll(-1).throttle<0,"Disconnected joystick must not issue thrust");
        axes[3]=-.95f;require(poll().throttle<0,"Reconnected throttle must rearm from its new position");
        require(poll(0,-1).throttle<0,"Keyboard-only throttle must remain disabled");
        require(poll(0,3,false).throttle==1,"Disabling launch suppression must apply the initial throttle");
        state.Reset();axes[3]=-.5f;
        require(poll(0,3,false,5000).throttle==1,"Changed saturation must affect thrust");
        state.Reset();axes[3]=std::numeric_limits<float>::infinity();
        require(poll(0,3,false).throttle<0,"Invalid throttle data must not issue thrust");
        state.Reset();axes[3]=-1;
        require(poll(0,3,true,9500,true).throttle<0,"Reversed throttle must start unarmed at idle");
        axes[3]=1;
        require(poll(0,3,true,9500,true).throttle==1,"Advancing the reversed throttle must command full thrust");
        axes[3]=-1;
        require(poll(0,3,true,9500,true).throttle==0,"Returning the reversed throttle to idle must cut thrust");
        require(poll(0,3,true,9500,false).throttle<0,"Changing throttle direction must rearm the control");
        std::cout<<"Native joystick calibration, throttle arming, disconnect and reassignment passed\n";
        return 0;
    } catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 1;}
}
