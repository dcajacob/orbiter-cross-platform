// Licensed under the MIT License
// Reuse the immutable observation driver; override only its SDK input schedule.
#define ORBITER_MODULE
#include "Orbitersdk.h"
#define GroundFlight FrozenGroundFlight
#include "../GroundFlight/Schedules.h"
#undef GroundFlight
#include "Controls.h"
namespace production_test {
inline void GroundFlight(VESSEL* vessel,const std::string& id,unsigned tick) {
    if(id=="pb_takeoff_landing")ControlledLanding(vessel,tick);
    else FrozenGroundFlight(vessel,id,tick);
}
}
#include "../BehaviorDriver.cpp"
