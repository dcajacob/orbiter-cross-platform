// Copyright (c) Orbiter contributors. Licensed under the MIT License.
// Shared test inputs, applied to the real vessel SDK on each platform.
#ifndef ORBITER_TEST_STOCK_CONTROL_SCHEDULES_H
#define ORBITER_TEST_STOCK_CONTROL_SCHEDULES_H
namespace production_test {
inline void Rcs(VESSEL* vessel,unsigned tick)
{
    const THGROUP_TYPE groups[]={THGROUP_ATT_PITCHUP,THGROUP_ATT_PITCHDOWN,THGROUP_ATT_YAWLEFT,
        THGROUP_ATT_YAWRIGHT,THGROUP_ATT_BANKLEFT,THGROUP_ATT_BANKRIGHT,THGROUP_ATT_UP,THGROUP_ATT_DOWN,
        THGROUP_ATT_LEFT,THGROUP_ATT_RIGHT,THGROUP_ATT_FORWARD,THGROUP_ATT_BACK};
    for(auto group:groups) vessel->SetThrusterGroupLevel(group,0);
    if(tick/40<12 && tick%40<8) vessel->SetThrusterGroupLevel(groups[tick/40],.2);
}
inline int Autopilot(VESSEL* vessel,unsigned tick)
{
    const int modes[]={NAVMODE_KILLROT,NAVMODE_PROGRADE,NAVMODE_RETROGRADE,NAVMODE_NORMAL,NAVMODE_ANTINORMAL};
    if(tick%80==0 && tick/80<5) {
        for(int mode:modes) vessel->DeactivateNavmode(mode);
        vessel->ActivateNavmode(modes[tick/80]);return modes[tick/80];
    }
    return 0;
}
}
#endif
