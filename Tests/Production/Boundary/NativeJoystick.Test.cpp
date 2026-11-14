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
        constexpr std::string_view velocityOnePc = "03000000f51000005570000011010000";
        unsigned char buttons[7] = {};
        buttons[2] = 1;
        require(NativeJoystickAlternate(buttons, 7, ""), "Other sticks must retain button 3");
        require(!NativeJoystickAlternate(buttons, 7, velocityOnePc), "VelocityOne PC mode must not use button 3");
        buttons[6] = 1;
        require(NativeJoystickAlternate(buttons, 7, velocityOnePc), "VelocityOne PC X must use button 7");
        require(!NativeJoystickAlternate(buttons, 6, velocityOnePc), "Truncated button list must not activate yaw");
        require(!NativeJoystickAlternate(nullptr, 0, velocityOnePc), "Disconnected stick must not activate yaw");
        buttons[6] = 0;
        require(!NativeJoystickAlternate(buttons, 7, velocityOnePc), "Releasing X must restore roll");
        NativeJoystickState state;
        float axes[]={.5f,-.5f,0,0};
        auto poll=[&](int device=0,int throttle=3,bool ignore=true,int saturation=9500,bool invert=false) {
            FlightInput input;
            state.Poll(device,axes,4,2,throttle,2500,saturation,ignore,input,invert);
            return input;
        };
        auto input=poll();
        require(input.x==0 && input.y==0 && input.rz==0,"Steering must first report center");
        require(input.throttle<0,"Initial throttle must be ignored");
        axes[0]=.02f;axes[1]=-.02f;
        input=poll();
        require(input.x==0 && input.y==0 && input.rz==0,"Centered stick must not command steering");
        axes[0]=.5f;axes[1]=-.5f;
        input=poll();
        require(input.x==333 && input.y==-333 && input.rz==0,"Calibrated controls did not reach FlightInput");
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

        state.Reset();
        const auto steeringNeutral=[](const FlightInput& input) {
            return input.x==0 && input.y==0 && input.rz==0;
        };
        axes[0]=axes[1]=axes[2]=axes[3]=-1;
        for(int frame=0;frame<60;++frame) {
            input=poll(0,3,true,9500,true);
            require(steeringNeutral(input) && input.throttle<0,"Uninitialized endpoint readings must not fire RCS or throttle");
        }
        axes[0]=axes[1]=0;
        axes[2]=std::numeric_limits<float>::quiet_NaN();
        require(steeringNeutral(poll()),"Invalid twist data must not arm steering");
        axes[0]=1;axes[2]=0;
        require(steeringNeutral(poll()),"Neutral on the other axes must not arm an off-center stick");
        axes[0]=0;
        require(steeringNeutral(poll()),"Centering must arm steering without firing");
        axes[0]=axes[1]=axes[2]=-1;
        input=poll();
        require(input.x==-1000 && input.y==-1000 && input.rz==-1000,"Once armed, legitimate full travel must still work");
        require(steeringNeutral(poll(-1)),"Removing the device must cut steering");
        require(steeringNeutral(poll()),"A reconnected stick must report center again");
        axes[0]=axes[1]=axes[2]=0;
        poll();
        axes[0]=1;
        require(poll().x==1000,"Steering must come back after reconnecting and centering");
        state.DeviceChanged(1);
        require(poll().x==1000,"Another device changing slots must not disarm this stick");
        state.DeviceChanged(0);
        require(steeringNeutral(poll()),"A replacement in the same GLFW slot must rearm steering");
        axes[0]=0;
        poll();
        axes[0]=1;
        require(poll(0,3,true,9500,true).x==1000,"Changing throttle direction must preserve armed steering");
        std::cout<<"Native joystick calibration, throttle arming, disconnect and reassignment passed\n";
        return 0;
    } catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 1;}
}
