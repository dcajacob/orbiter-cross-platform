// Copyright (c) Martin Schweiger
// Licensed under the MIT License
#include "FlightControls.h"
#include "Vessel.h"
#include "TimeData.h"
#include <algorithm>
#include <stdexcept>
namespace orbiter::production {
namespace {FlightControls* bound=nullptr;}
FlightControls* BindFlightControls(FlightControls* value) {auto* previous=bound;bound=value;return previous;}
FlightControls& GetFlightControls() {if(!bound)throw std::logic_error("No native flight input session");return *bound;}
void FlightControls::Immediate(Vessel& vessel,TimeData& td,FlightInput input) {
    std::fill(std::begin(keyboard),std::end(keyboard),0);
    std::fill(std::begin(joystick),std::end(joystick),0);
    Vessel* g_focusobj=&vessel;char* kstate=input.keys.data();bool bEnableAtt=true;
	if (!g_focusobj->ConsumeDirectKey (kstate)) {  // offer the snapshot to the original module first

	// main/retro/hover thruster settings
	if (keymap.IsLogicalKey (kstate, OAPI_LKEY_IncMainThrust))   g_focusobj->IncMainRetroLevel ( 0.2*td.SimDT);
	if (keymap.IsLogicalKey (kstate, OAPI_LKEY_DecMainThrust))   g_focusobj->IncMainRetroLevel (-0.2*td.SimDT);
	if (keymap.IsLogicalKey (kstate, OAPI_LKEY_KillMainRetro)) { g_focusobj->SetThrusterGroupLevel (THGROUP_MAIN, 0.0);
		                                                         g_focusobj->SetThrusterGroupLevel (THGROUP_RETRO, 0.0); }
	if (keymap.IsLogicalKey (kstate, OAPI_LKEY_FullMainThrust))  g_focusobj->OverrideMainLevel ( 1.0);
	if (keymap.IsLogicalKey (kstate, OAPI_LKEY_FullRetroThrust)) g_focusobj->OverrideMainLevel (-1.0);
	if (keymap.IsLogicalKey (kstate, OAPI_LKEY_IncHoverThrust))  g_focusobj->IncThrusterGroupLevel (THGROUP_HOVER,  0.2*td.SimDT);
	if (keymap.IsLogicalKey (kstate, OAPI_LKEY_DecHoverThrust))  g_focusobj->IncThrusterGroupLevel (THGROUP_HOVER, -0.2*td.SimDT);

	// Reaction control system
	if (bEnableAtt) {
		// rotational mode
		if      (keymap.IsLogicalKey (kstate, OAPI_LKEY_RCSPitchUp))     keyboard[THGROUP_ATT_PITCHUP]   = 1000;
		else if (keymap.IsLogicalKey (kstate, OAPI_LKEY_LPRCSPitchUp))   keyboard[THGROUP_ATT_PITCHUP]   =  100;
		if      (keymap.IsLogicalKey (kstate, OAPI_LKEY_RCSPitchDown))   keyboard[THGROUP_ATT_PITCHDOWN] = 1000;
		else if (keymap.IsLogicalKey (kstate, OAPI_LKEY_LPRCSPitchDown)) keyboard[THGROUP_ATT_PITCHDOWN] =  100;
		if      (keymap.IsLogicalKey (kstate, OAPI_LKEY_RCSYawLeft))     keyboard[THGROUP_ATT_YAWLEFT]   = 1000;
		else if (keymap.IsLogicalKey (kstate, OAPI_LKEY_LPRCSYawLeft))   keyboard[THGROUP_ATT_YAWLEFT]   =  100;
		if      (keymap.IsLogicalKey (kstate, OAPI_LKEY_RCSYawRight))    keyboard[THGROUP_ATT_YAWRIGHT]  = 1000;
		else if (keymap.IsLogicalKey (kstate, OAPI_LKEY_LPRCSYawRight))  keyboard[THGROUP_ATT_YAWRIGHT]  =  100;
		if      (keymap.IsLogicalKey (kstate, OAPI_LKEY_RCSBankLeft))    keyboard[THGROUP_ATT_BANKLEFT]  = 1000;
		else if (keymap.IsLogicalKey (kstate, OAPI_LKEY_LPRCSBankLeft))  keyboard[THGROUP_ATT_BANKLEFT]  =  100;
		if      (keymap.IsLogicalKey (kstate, OAPI_LKEY_RCSBankRight))   keyboard[THGROUP_ATT_BANKRIGHT] = 1000;
		else if (keymap.IsLogicalKey (kstate, OAPI_LKEY_LPRCSBankRight)) keyboard[THGROUP_ATT_BANKRIGHT] =  100;
		// linear mode
		if      (keymap.IsLogicalKey (kstate, OAPI_LKEY_RCSUp))          keyboard[THGROUP_ATT_UP]        = 1000;
		else if (keymap.IsLogicalKey (kstate, OAPI_LKEY_LPRCSUp))        keyboard[THGROUP_ATT_UP]        =  100;
		if      (keymap.IsLogicalKey (kstate, OAPI_LKEY_RCSDown))        keyboard[THGROUP_ATT_DOWN]      = 1000;
		else if (keymap.IsLogicalKey (kstate, OAPI_LKEY_LPRCSDown))      keyboard[THGROUP_ATT_DOWN]      =  100;
		if      (keymap.IsLogicalKey (kstate, OAPI_LKEY_RCSLeft))        keyboard[THGROUP_ATT_LEFT]      = 1000;
		else if (keymap.IsLogicalKey (kstate, OAPI_LKEY_LPRCSLeft))      keyboard[THGROUP_ATT_LEFT]      =  100;
		if      (keymap.IsLogicalKey (kstate, OAPI_LKEY_RCSRight))       keyboard[THGROUP_ATT_RIGHT]     = 1000;
		else if (keymap.IsLogicalKey (kstate, OAPI_LKEY_LPRCSRight))     keyboard[THGROUP_ATT_RIGHT]     =  100;
		if      (keymap.IsLogicalKey (kstate, OAPI_LKEY_RCSForward))     keyboard[THGROUP_ATT_FORWARD]   = 1000;
		else if (keymap.IsLogicalKey (kstate, OAPI_LKEY_LPRCSForward))   keyboard[THGROUP_ATT_FORWARD]   =  100;
		if      (keymap.IsLogicalKey (kstate, OAPI_LKEY_RCSBack))        keyboard[THGROUP_ATT_BACK]      = 1000;
		else if (keymap.IsLogicalKey (kstate, OAPI_LKEY_LPRCSBack))      keyboard[THGROUP_ATT_BACK]      =  100;
	}

	// Elevator trim control
	if (keymap.IsLogicalKey (kstate, OAPI_LKEY_IncElevatorTrim)) g_focusobj->IncTrim (AIRCTRL_ELEVATORTRIM);
	if (keymap.IsLogicalKey (kstate, OAPI_LKEY_DecElevatorTrim)) g_focusobj->DecTrim (AIRCTRL_ELEVATORTRIM);

	// Wheel brake control
	if (keymap.IsLogicalKey (kstate, OAPI_LKEY_WheelbrakeLeft))  g_focusobj->SetWBrakeLevel (1.0, 1, false);
	if (keymap.IsLogicalKey (kstate, OAPI_LKEY_WheelbrakeRight)) g_focusobj->SetWBrakeLevel (1.0, 2, false);

    }
	if (bEnableAtt) {
		if (input.x) {
			if (input.alternate) { // emulate rudder control
				if (input.x > 0) joystick[THGROUP_ATT_YAWRIGHT] =   input.x;
				else            joystick[THGROUP_ATT_YAWLEFT]  =  -input.x;
			} else {                 // rotation (bank)
				if (input.x > 0) joystick[THGROUP_ATT_BANKRIGHT] =  input.x;
				else            joystick[THGROUP_ATT_BANKLEFT]  = -input.x;
			}
		}
		if (input.y) {                // rotation (pitch) or translation (vertical)
			if (input.y > 0) joystick[THGROUP_ATT_PITCHUP]   = joystick[THGROUP_ATT_UP]    =  input.y;
			else            joystick[THGROUP_ATT_PITCHDOWN] = joystick[THGROUP_ATT_DOWN]  = -input.y;
		}
		if (input.rz) {               // rotation (yaw) or translation (transversal)
			if (input.rz > 0) joystick[THGROUP_ATT_YAWRIGHT] = joystick[THGROUP_ATT_RIGHT] =  input.rz;
			else             joystick[THGROUP_ATT_YAWLEFT]  = joystick[THGROUP_ATT_LEFT]  = -input.rz;
		}
	}

    if(input.throttle>=0) {vessel.SetThrusterGroupLevel(THGROUP_MAIN,input.throttle);vessel.SetThrusterGroupLevel(THGROUP_RETRO,0);}
    UInt32 total[15];for(unsigned i=0;i<15;++i)total[i]=keyboard[i]+joystick[i];
    vessel.ApplyUserAttitudeControls(total);
}
int FlightControls::DefaultBuffered(Vessel& vessel,UInt32 key,bool down,char* kstate) {
    if(!down)return 0;
	// Navigation computer modes
	if (keymap.IsLogicalKey (key, kstate, OAPI_LKEY_NMHoldAltitude)) vessel.TglNavMode (NAVMODE_HOLDALT);
	if (keymap.IsLogicalKey (key, kstate, OAPI_LKEY_NMHLevel))       vessel.TglNavMode (NAVMODE_HLEVEL);
	if (keymap.IsLogicalKey (key, kstate, OAPI_LKEY_NMPrograde))     vessel.TglNavMode (NAVMODE_PROGRADE);
	if (keymap.IsLogicalKey (key, kstate, OAPI_LKEY_NMRetrograde))   vessel.TglNavMode (NAVMODE_RETROGRADE);
	if (keymap.IsLogicalKey (key, kstate, OAPI_LKEY_NMNormal))       vessel.TglNavMode (NAVMODE_NORMAL);
	if (keymap.IsLogicalKey (key, kstate, OAPI_LKEY_NMAntinormal))   vessel.TglNavMode (NAVMODE_ANTINORMAL);
	if (keymap.IsLogicalKey (key, kstate, OAPI_LKEY_NMKillrot))      vessel.TglNavMode (NAVMODE_KILLROT);
	if (keymap.IsLogicalKey (key, kstate, OAPI_LKEY_RCSEnable))      vessel.SetAttMode (vessel.AttMode() >= 1 ? 0 : 1);
	if (keymap.IsLogicalKey (key, kstate, OAPI_LKEY_RCSMode))        vessel.ToggleAttMode ();
	if (keymap.IsLogicalKey (key, kstate, OAPI_LKEY_Undock))         vessel.UndockInteractive ();

    return 0;
}
double FlightControls::Manual(unsigned group,unsigned device) const {
    if(group>=15) return 0;
    return .001*(device==0?keyboard[group]:device==1?joystick[group]:keyboard[group]+joystick[group]);
}
}
