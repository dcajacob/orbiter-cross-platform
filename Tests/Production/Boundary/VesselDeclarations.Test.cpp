// Licensed under the MIT License
#include "Vessel.h"
#include "SuperVessel.h"
#include <cstddef>
#include <type_traits>
// The original packed-state byte buffer is persisted by the production
// Windows application. Naming its two union views must not move its fields.
static_assert(std::is_standard_layout<ScenarioData>::value);
static_assert(sizeof(ScenarioData)==120);
static_assert(offsetof(ScenarioData,size)==0 && offsetof(ScenarioData,flag)==4);
static_assert(offsetof(ScenarioData,fstate)==8 && offsetof(ScenarioData,orbital)==16);
static_assert(offsetof(ScenarioData,landed)==16 && offsetof(ScenarioData,buf)==112);
static_assert(std::is_base_of<VesselBase,Vessel>::value);
static_assert(std::is_base_of<VesselBase,SuperVessel>::value);
int main() {return 0;}
