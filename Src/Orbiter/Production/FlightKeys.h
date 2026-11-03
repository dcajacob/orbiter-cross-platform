// Copyright (c) Martin Schweiger
// Licensed under the MIT License
// Internal native input protocol: verbatim public SDK key codes and modifiers.
#pragma once
#define OAPI_KEY_ESCAPE			0x01  ///< Escape key
#define OAPI_KEY_1				0x02  ///< '1' key on main keyboard
#define OAPI_KEY_2				0x03  ///< '2' key on main keyboard
#define OAPI_KEY_3				0x04  ///< '3' key on main keyboard
#define OAPI_KEY_4				0x05  ///< '4' key on main keyboard
#define OAPI_KEY_5				0x06  ///< '5' key on main keyboard
#define OAPI_KEY_6				0x07  ///< '6' key on main keyboard
#define OAPI_KEY_7				0x08  ///< '7' key on main keyboard
#define OAPI_KEY_8				0x09  ///< '8' key on main keyboard
#define OAPI_KEY_9				0x0A  ///< '9' key on main keyboard
#define OAPI_KEY_0				0x0B  ///< '0' key on main keyboard
#define OAPI_KEY_MINUS			0x0C  ///< '-' key on main keyboard
#define OAPI_KEY_EQUALS			0x0D  ///< '=' key on main keyboard
#define OAPI_KEY_BACK			0x0E  ///< backspace key
#define OAPI_KEY_TAB			0x0F  ///< tab key
#define OAPI_KEY_Q				0x10  ///< 'Q' key
#define OAPI_KEY_W				0x11  ///< 'W' key
#define OAPI_KEY_E				0x12  ///< 'E' key
#define OAPI_KEY_R				0x13  ///< 'R' key
#define OAPI_KEY_T				0x14  ///< 'T' key
#define OAPI_KEY_Y				0x15  ///< 'Y' key
#define OAPI_KEY_U				0x16  ///< 'U' key
#define OAPI_KEY_I				0x17  ///< 'I' key
#define OAPI_KEY_O				0x18  ///< 'O' key
#define OAPI_KEY_P				0x19  ///< 'P' key
#define OAPI_KEY_LBRACKET		0x1A  ///< '[' (left bracket) key
#define OAPI_KEY_RBRACKET		0x1B  ///< ']' (right bracket) key
#define OAPI_KEY_RETURN			0x1C  ///< 'Enter' key on main keyboard
#define OAPI_KEY_LCONTROL		0x1D  ///< Left 'Ctrl' key
#define OAPI_KEY_A				0x1E  ///< 'A' key
#define OAPI_KEY_S				0x1F  ///< 'S' key
#define OAPI_KEY_D				0x20  ///< 'D' key
#define OAPI_KEY_F				0x21  ///< 'F' key
#define OAPI_KEY_G				0x22  ///< 'G' key
#define OAPI_KEY_H				0x23  ///< 'H' key
#define OAPI_KEY_J				0x24  ///< 'J' key
#define OAPI_KEY_K				0x25  ///< 'K' key
#define OAPI_KEY_L				0x26  ///< 'L' key
#define OAPI_KEY_SEMICOLON		0x27  ///< ';' (semicolon) key
#define OAPI_KEY_APOSTROPHE		0x28  ///< ' (apostrophe) key
#define OAPI_KEY_GRAVE			0x29  ///< accent grave
#define OAPI_KEY_LSHIFT			0x2A  ///< Left 'Shift' key
#define OAPI_KEY_BACKSLASH		0x2B  ///< '\' (Backslash) key
#define OAPI_KEY_Z				0x2C  ///< 'Z' key
#define OAPI_KEY_X				0x2D  ///< 'X' key
#define OAPI_KEY_C				0x2E  ///< 'C' key
#define OAPI_KEY_V				0x2F  ///< 'V' key
#define OAPI_KEY_B				0x30  ///< 'B' key
#define OAPI_KEY_N				0x31  ///< 'N' key
#define OAPI_KEY_M				0x32  ///< 'M' key
#define OAPI_KEY_COMMA			0x33  ///< ',' (comma) key
#define OAPI_KEY_PERIOD			0x34  ///< '.' key on main keyboard
#define OAPI_KEY_SLASH			0x35  ///< '/' key on main keyboard
#define OAPI_KEY_RSHIFT			0x36  ///< Right 'Shift' key
#define OAPI_KEY_MULTIPLY		0x37  ///< * on numeric keypad
#define OAPI_KEY_LALT			0x38  ///< left Alt
#define OAPI_KEY_SPACE			0x39  ///< 'Space' key
#define OAPI_KEY_CAPITAL		0x3A  ///< caps lock key
#define OAPI_KEY_F1				0x3B  ///< F1 function key
#define OAPI_KEY_F2				0x3C  ///< F2 function key
#define OAPI_KEY_F3				0x3D  ///< F3 function key
#define OAPI_KEY_F4				0x3E  ///< F4 function key
#define OAPI_KEY_F5				0x3F  ///< F5 function key
#define OAPI_KEY_F6				0x40  ///< F6 function key
#define OAPI_KEY_F7				0x41  ///< F7 function key
#define OAPI_KEY_F8				0x42  ///< F8 function key
#define OAPI_KEY_F9				0x43  ///< F9 function key
#define OAPI_KEY_F10			0x44  ///< F10 function key
#define OAPI_KEY_NUMLOCK		0x45  ///< 'Num Lock' key
#define OAPI_KEY_SCROLL			0x46  ///< Scroll lock
#define OAPI_KEY_NUMPAD7		0x47  ///< '7' key on numeric keypad
#define OAPI_KEY_NUMPAD8		0x48  ///< '8' key on numeric keypad
#define OAPI_KEY_NUMPAD9		0x49  ///< '9' key on numeric keypad
#define OAPI_KEY_SUBTRACT		0x4A  ///< '-' key on numeric keypad
#define OAPI_KEY_NUMPAD4		0x4B  ///< '4' key on numeric keypad
#define OAPI_KEY_NUMPAD5		0x4C  ///< '5' key on numeric keypad
#define OAPI_KEY_NUMPAD6		0x4D  ///< '6' key on numeric keypad
#define OAPI_KEY_ADD			0x4E  ///< '+' key on numeric keypad
#define OAPI_KEY_NUMPAD1		0x4F  ///< '1' key on numeric keypad
#define OAPI_KEY_NUMPAD2		0x50  ///< '2' key on numeric keypad
#define OAPI_KEY_NUMPAD3		0x51  ///< '3' key on numeric keypad
#define OAPI_KEY_NUMPAD0		0x52  ///< '0' key on numeric keypad
#define OAPI_KEY_DECIMAL		0x53  ///< '.' key on numeric keypad
#define OAPI_KEY_OEM_102		0x56  ///< | \< \> on UK/German keyboards
#define OAPI_KEY_F11			0x57  ///< F11 function key
#define OAPI_KEY_F12			0x58  ///< F12 function key
#define OAPI_KEY_NUMPADENTER	0x9C  ///< Enter on numeric keypad
#define OAPI_KEY_RCONTROL		0x9D  ///< right Control key
#define OAPI_KEY_DIVIDE			0xB5  ///< '/' key on numeric keypad
#define OAPI_KEY_SYSRQ          0xB7  ///< SysRq/PrtScn key
#define OAPI_KEY_RALT           0xB8  ///< right Alt
#define OAPI_KEY_PAUSE          0xC5  ///< Break/Pause key
#define OAPI_KEY_HOME           0xC7  ///< Home on cursor keypad
#define OAPI_KEY_UP             0xC8  ///< up-arrow on cursor keypad
#define OAPI_KEY_PRIOR          0xC9  ///< PgUp on cursor keypad
#define OAPI_KEY_LEFT           0xCB  ///< left-arrow on cursor keypad
#define OAPI_KEY_RIGHT          0xCD  ///< right-arrow on cursor keypad
#define OAPI_KEY_END            0xCF  ///< End on cursor keypad
#define OAPI_KEY_DOWN           0xD0  ///< down-arrow on cursor keypad
#define OAPI_KEY_NEXT           0xD1  ///< PgDn on cursor keypad
#define OAPI_KEY_INSERT         0xD2  ///< Insert on cursor keypad
#define OAPI_KEY_DELETE         0xD3  ///< Delete on cursor keypad
#define KEYDOWN(buf,key) (buf[key] & 0x80)
#define RESETKEY(buf,key) (buf[key] = 0)
#define KEYMOD_LSHIFT(buf)   (KEYDOWN(buf,OAPI_KEY_LSHIFT))
#define KEYMOD_RSHIFT(buf)   (KEYDOWN(buf,OAPI_KEY_RSHIFT))
#define KEYMOD_SHIFT(buf)    (KEYMOD_LSHIFT(buf) || KEYMOD_RSHIFT(buf))
#define KEYMOD_LCONTROL(buf) (KEYDOWN(buf,OAPI_KEY_LCONTROL))
#define KEYMOD_RCONTROL(buf) (KEYDOWN(buf,OAPI_KEY_RCONTROL))
#define KEYMOD_CONTROL(buf)  (KEYMOD_LCONTROL(buf) || KEYMOD_RCONTROL(buf))
#define KEYMOD_LALT(buf)     (KEYDOWN(buf,OAPI_KEY_LALT))
#define KEYMOD_RALT(buf)     (KEYDOWN(buf,OAPI_KEY_RALT))
#define KEYMOD_ALT(buf)      (KEYMOD_LALT(buf) || KEYMOD_RALT(buf))
#define OAPI_LKEY_CockpitRotateLeft  0 ///< rotate camera left in cockpit view
#define OAPI_LKEY_CockpitRotateRight 1 ///< rotate camera right in cockpit view
#define OAPI_LKEY_CockpitRotateUp    2 ///< rotate camera up in cockpit view
#define OAPI_LKEY_CockpitRotateDown  3 ///< rotate camera down in cockpit view
#define OAPI_LKEY_CockpitDontLean    4 ///< return to default cockpit camera position
#define OAPI_LKEY_CockpitLeanForward 5 ///< move cockpit camera forward
#define OAPI_LKEY_CockpitLeanLeft    6 ///< move cockpit camera left
#define OAPI_LKEY_CockpitLeanRight   7 ///< move cockpit camera right
#define OAPI_LKEY_CockpitResetCam    8 ///< rotate and shift cockpit camera back to default
#define OAPI_LKEY_PanelShiftLeft     9 ///< shift 2D instrument panel left
#define OAPI_LKEY_PanelShiftRight   10 ///< shift 2D instrument panel right
#define OAPI_LKEY_PanelShiftUp      11 ///< shift 2D instrument panel up
#define OAPI_LKEY_PanelShiftDown    12 ///< shift 2D instrument panel down
#define OAPI_LKEY_PanelSwitchLeft   13 ///< switch to left neighbour panel
#define OAPI_LKEY_PanelSwitchRight  14 ///< switch to right neighbour panel
#define OAPI_LKEY_PanelSwitchUp     15 ///< switch to upper neighbour panel
#define OAPI_LKEY_PanelSwitchDown   16 ///< switch to lower neighbour panel
#define OAPI_LKEY_TrackRotateLeft   17 ///< turn track view camera left
#define OAPI_LKEY_TrackRotateRight  18 ///< turn track view camera right
#define OAPI_LKEY_TrackRotateUp     19 ///< turn track view camera up
#define OAPI_LKEY_TrackRotateDown   20 ///< turn track view camera down
#define OAPI_LKEY_TrackAdvance      21 ///< advance track view camera towards target
#define OAPI_LKEY_TrackRetreat      22 ///< retreat track view camera from target
#define OAPI_LKEY_GroundTiltLeft    23 ///< tilt camera left in ground view
#define OAPI_LKEY_GroundTiltRight   24 ///< tilt camera right in ground view
#define OAPI_LKEY_GroundTiltUp      25 ///< tilt camera up in ground view
#define OAPI_LKEY_GroundTiltDown    26 ///< tilt camera down in ground view
#define OAPI_LKEY_IncMainThrust     27 ///< increment thrust of main thrusters
#define OAPI_LKEY_DecMainThrust     28 ///< decrement thrust of main thrusters
#define OAPI_LKEY_KillMainRetro     29 ///< kill main and retro thrusters
#define OAPI_LKEY_FullMainThrust    30 ///< temporary full main thrust
#define OAPI_LKEY_FullRetroThrust   31 ///< temporary full retro thrust
#define OAPI_LKEY_IncHoverThrust    32 ///< increment thrust of hover thrusters
#define OAPI_LKEY_DecHoverThrust    33 ///< decrement thrust of hover thrusters
#define OAPI_LKEY_RCSEnable         34 ///< enable/disable RCS (reaction control system)
#define OAPI_LKEY_RCSMode           35 ///< toggle linear/rotational RCS mode
#define OAPI_LKEY_RCSPitchUp        36 ///< rotational RCS: pitch up
#define OAPI_LKEY_RCSPitchDown      37 ///< rotational RCS: pitch down
#define OAPI_LKEY_RCSYawLeft        38 ///< rotational RCS: yaw left
#define OAPI_LKEY_RCSYawRight       39 ///< rotational RCS: yaw right
#define OAPI_LKEY_RCSBankLeft       40 ///< rotational RCS: bank left
#define OAPI_LKEY_RCSBankRight      41 ///< rotational RCS: bank right
#define OAPI_LKEY_RCSUp             42 ///< linear RCS: accelerate up (+y)
#define OAPI_LKEY_RCSDown           43 ///< linear RCS: accelerate down (-y)
#define OAPI_LKEY_RCSLeft           44 ///< linear RCS: accelerate left (-x)
#define OAPI_LKEY_RCSRight          45 ///< linear RCS: accelerate right (+x)
#define OAPI_LKEY_RCSForward        46 ///< linear RCS: accelerate forward (+z)
#define OAPI_LKEY_RCSBack           47 ///< linear RCS: accelerate backward (-z)
#define OAPI_LKEY_LPRCSPitchUp      48 ///< rotational RCS: pitch up 10%
#define OAPI_LKEY_LPRCSPitchDown    49 ///< rotational RCS: pitch down 10%
#define OAPI_LKEY_LPRCSYawLeft      50 ///< rotational RCS: yaw left 10%
#define OAPI_LKEY_LPRCSYawRight     51 ///< rotational RCS: yaw right 10%
#define OAPI_LKEY_LPRCSBankLeft     52 ///< rotational RCS: bank left 10%
#define OAPI_LKEY_LPRCSBankRight    53 ///< rotational RCS: bank right 10%
#define OAPI_LKEY_LPRCSUp           54 ///< linear RCS: accelerate up 10% (+y)
#define OAPI_LKEY_LPRCSDown         55 ///< linear RCS: accelerate down 10% (-y)
#define OAPI_LKEY_LPRCSLeft         56 ///< linear RCS: accelerate left 10% (-x)
#define OAPI_LKEY_LPRCSRight        57 ///< linear RCS: accelerate right 10% (+x)
#define OAPI_LKEY_LPRCSForward      58 ///< linear RCS: accelerate forward 10% (+z)
#define OAPI_LKEY_LPRCSBack         59 ///< linear RCS: accelerate backward 10% (-z)
#define OAPI_LKEY_NMHoldAltitude    60 ///< toggle navmode: hold altitude
#define OAPI_LKEY_NMHLevel          61 ///< toggle navmode: level with horizon
#define OAPI_LKEY_NMPrograde        62 ///< toggle navmode: prograde
#define OAPI_LKEY_NMRetrograde      63 ///< toggle navmode: retrograde
#define OAPI_LKEY_NMNormal          64 ///< toggle navmode: normal to orbital plane
#define OAPI_LKEY_NMAntinormal      65 ///< toggle navmode: antinormal to orbital plane
#define OAPI_LKEY_NMKillrot         66 ///< toggle navmode: kill rotation
#define OAPI_LKEY_Undock            67 ///< undock from docked vessel
#define OAPI_LKEY_IncElevatorTrim   68 ///< increment elevator trim setting
#define OAPI_LKEY_DecElevatorTrim   69 ///< decrement elevator trim setting
#define OAPI_LKEY_WheelbrakeLeft    70 ///< apply wheelbrake left
#define OAPI_LKEY_WheelbrakeRight   71 ///< apply wheelbrake right
#define OAPI_LKEY_HUD               72 ///< toggle HUD on/off
#define OAPI_LKEY_HUDMode           73 ///< switch through HUD modes
#define OAPI_LKEY_HUDReference      74 ///< query reference object for HUD display
#define OAPI_LKEY_HUDTarget         75 ///< query target object for HUD display
#define OAPI_LKEY_HUDColour         76 ///< switch through HUD colours
#define OAPI_LKEY_IncSimSpeed       77 ///< increase simulation speed x10
#define OAPI_LKEY_DecSimSpeed       78 ///< decrease simulation speed x0.1
#define OAPI_LKEY_IncFOV            79 ///< increment field of view
#define OAPI_LKEY_DecFOV            80 ///< decrement field of view
#define OAPI_LKEY_StepIncFOV        81 ///< increment field of view by 10 deg
#define OAPI_LKEY_StepDecFOV        82 ///< decrement field of view by 10 deg
#define OAPI_LKEY_MainMenu          83 ///< open main menu
#define OAPI_LKEY_DlgHelp           84 ///< open help dialog
#define OAPI_LKEY_DlgCamera         85 ///< open camera dialog
#define OAPI_LKEY_DlgSimspeed       86 ///< open simulation speed dialog
#define OAPI_LKEY_DlgCustomCmd      87 ///< open custom command dialog
#define OAPI_LKEY_DlgVisHelper      88 ///< open visual helper dialog
#define OAPI_LKEY_DlgRecorder       89 ///< open flight recorder dialog
#define OAPI_LKEY_DlgInfo           90 ///< open object info dialog
#define OAPI_LKEY_DlgMap            91 ///< open map dialog
#define OAPI_LKEY_ToggleCamInternal 92 ///< switch between cockpit and external camera
#define OAPI_LKEY_ToggleTrackMode   93 ///< switch between track camera modes
#define OAPI_LKEY_TogglePanelMode   94 ///< switch between cockpit modes
#define OAPI_LKEY_TogglePlanetarium 95 ///< toggle celestial marker display on/off
#define OAPI_LKEY_ToggleLabels      96 ///< toggle object and surface markers on/off
#define OAPI_LKEY_ToggleRecPlay     97 ///< toggle flight recorder/playback on/off
#define OAPI_LKEY_Pause             98 ///< toggle simulation pause on/off
#define OAPI_LKEY_Quicksave         99 ///< quick-save current simulation state
#define OAPI_LKEY_Quit             100 ///< quit simulation session
#define OAPI_LKEY_DlgSelectVessel  101 ///< open vessel selection dialog
#define OAPI_LKEY_SelectPrevVessel 102 ///< switch focus to previous vessel
#define OAPI_LKEY_DlgCapture       103 ///< open screen capture dialog
#define OAPI_LKEY_DlgOptions       104 ///< open options dialog
#define LKEY_COUNT 105                 ///< number of logical key definitions
