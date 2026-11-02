// Licensed under the MIT License
#include "NativeObservation/ApplicationObservation.h"
namespace {
thread_local orbiter::production::VesselObserver observer=nullptr;
thread_local void* context=nullptr;
}
void orbiter::production::BindVesselObserver(VesselObserver next,void* value) {observer=next;context=value;}
extern "C" void OrbiterTestObserve(const char* phase,const char* object,double seconds,double mjd,int running) {
    if(observer)observer(context,phase,object,seconds,mjd,running);
}
