// Licensed under the MIT License
#pragma once
namespace production_test {
// Recorded controls only. The actual production SDK supplies every force.
inline void ManualFlight(VESSEL* v,unsigned tick) {
    v->SetThrusterGroupLevel(THGROUP_MAIN,tick<40?.2:0);
    v->SetThrusterGroupLevel(THGROUP_HOVER,tick>=40 && tick<60?.1:0);
    const THGROUP_TYPE groups[]={THGROUP_ATT_PITCHUP,THGROUP_ATT_PITCHDOWN,THGROUP_ATT_YAWLEFT,
        THGROUP_ATT_YAWRIGHT,THGROUP_ATT_BANKLEFT,THGROUP_ATT_BANKRIGHT,THGROUP_ATT_UP,THGROUP_ATT_DOWN,
        THGROUP_ATT_LEFT,THGROUP_ATT_RIGHT,THGROUP_ATT_FORWARD,THGROUP_ATT_BACK};
    if(tick>=80 && tick<560) {
        unsigned slot=(tick-80)/40;
        v->SetAttitudeMode(slot<6?1:2);
        if((tick-80)%40<8) v->IncThrusterGroupLevel_SingleStep(groups[slot],.2);
    }
    const int modes[]={NAVMODE_KILLROT,NAVMODE_PROGRADE,NAVMODE_RETROGRADE,NAVMODE_NORMAL,NAVMODE_ANTINORMAL};
    if(tick>=560 && tick<960 && (tick-560)%80==0) {
        for(auto mode:modes)v->DeactivateNavmode(mode);
        v->ActivateNavmode(modes[(tick-560)/80]);
    }
}
}
