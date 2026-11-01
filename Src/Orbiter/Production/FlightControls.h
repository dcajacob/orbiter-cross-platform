// Copyright (c) Martin Schweiger
// Licensed under the MIT License
#pragma once
#include "Export.h"
#include "FlightInput.h"
#include "Keymap.h"
class Vessel;class TimeData;
namespace orbiter::production {
class ORBITER_PRODUCTION_API FlightControls {
public:
    Keymap keymap;
    void Immediate(Vessel& vessel,TimeData& time,FlightInput input);
    int DefaultBuffered(Vessel& vessel,UInt32 key,bool down,char* state);
    double Manual(unsigned group,unsigned device) const;
private:
    UInt32 keyboard[15]{},joystick[15]{};
};
ORBITER_PRODUCTION_API FlightControls* BindFlightControls(FlightControls* controls);
ORBITER_PRODUCTION_API FlightControls& GetFlightControls();
}
