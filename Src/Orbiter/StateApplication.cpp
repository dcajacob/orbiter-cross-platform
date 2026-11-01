// Copyright (c) Martin Schweiger
// Licensed under the MIT License
// Original application clock/focus adapters for scenario metadata.
#include "Orbiter.h"
#include "State.h"
#include "Vessel.h"
#include "Astro.h"
#include <type_traits>
// ORBITER_PRODUCTION_OBSERVATION_BEGIN
#ifdef ORBITER_PRODUCTION_OBSERVATION
#include "ApplicationObservation.h"
#endif
// ORBITER_PRODUCTION_OBSERVATION_END
extern Vessel* g_focusobj;
extern TimeData td;
static_assert(std::is_same<orbiter::production::UInt32,DWORD>::value);
State::State() : State(MJD(time(NULL))) {}
void State::Update() { Update(td.MJD1,g_focusobj->Name()); }
bool State::Read(const char* fname)
{
    // Preserve the original failure path before consulting the clock/observer.
    std::ifstream input(fname,std::ios::in);
    if (!input) return false;
    double defaultMjd=MJD(time(NULL));
    defaultMjd+=UTC_CT_diff*day;
// ORBITER_PRODUCTION_OBSERVATION_BEGIN
#ifdef ORBITER_PRODUCTION_OBSERVATION
    defaultMjd=OrbiterTestDefaultMjd(defaultMjd);
#endif
// ORBITER_PRODUCTION_OBSERVATION_END
    return Read(input,std::filesystem::path(fname),defaultMjd);
}
