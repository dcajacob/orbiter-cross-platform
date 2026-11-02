// Licensed under the MIT License
#pragma once
namespace production_test {
// Only public stock SDK controls. The production altitude/attitude programs
// supply their original feedback and forces; no replacement controller or
// integrator is implemented here. Durations are declared before capture.
inline void ControlledLanding(VESSEL* vessel,unsigned tick) {
    if(tick==0) {
        vessel->ActivateNavmode(NAVMODE_HLEVEL);
        vessel->SetHoverHoldAltitude(12.,true);
    }
    if(tick==1200)vessel->SetHoverHoldAltitude(0.,true);
    if(tick>=4800) {
        vessel->DeactivateNavmode(NAVMODE_HOLDALT);
        vessel->DeactivateNavmode(NAVMODE_HLEVEL);
        vessel->SetThrusterGroupLevel(THGROUP_HOVER,0.);
    }
}
}
