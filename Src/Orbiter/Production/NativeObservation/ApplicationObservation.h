// Licensed under the MIT License
// Internal native observation binding for the original read-only vessel hooks.
// It is not installed and does not extend the Windows SDK.
#pragma once
extern "C" void OrbiterTestObserve(const char*,const char*,double,double,int);
namespace orbiter::production {
using VesselObserver=void(*)(void*,const char*,const char*,double,double,int);
void BindVesselObserver(VesselObserver,void*);
}
