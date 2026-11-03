// Copyright (c) Martin Schweiger
// Licensed under the MIT License
#ifndef ORBITER_VESSEL_DATA_H
#define ORBITER_VESSEL_DATA_H
#include "OrbiterVector.h"
class VESSEL;

// ===========================================================================
/// \ingroup defines
/// \defgroup refframe Identifiers for frames of reference
// ===========================================================================
//@{

/**
 * \brief Identifiers for frames of reference
 */
typedef enum {
	FRAME_GLOBAL,    ///< global (ecliptic) frame
	FRAME_LOCAL,     ///< local object frame
	FRAME_REFLOCAL,  ///< local reference object frame
	FRAME_HORIZON    ///< local horizon frame
} REFFRAME;

//@}

// ===========================================================================
/// \ingroup defines
/// \defgroup thrusterparam Thruster and thruster-group parameters
// ===========================================================================
//@{

/**
 * \brief Thruster group identifiers (obsolete)
 */
typedef enum {
	ENGINE_MAIN,     ///< main thrusters
	ENGINE_RETRO,    ///< retro thrusters
	ENGINE_HOVER,    ///< hover thrusters
	ENGINE_ATTITUDE  ///< attitude (RCS) thrusters
} ENGINETYPE;

typedef enum {
	EXHAUST_MAIN,
	EXHAUST_RETRO,
	EXHAUST_HOVER,
	EXHAUST_CUSTOM
} EXHAUSTTYPE;

/**
 * \brief Thruster group types
 * \sa VESSEL::CreateThrusterGroup
 */
enum THGROUP_TYPE {
	THGROUP_MAIN,            ///< main thrusters
	THGROUP_RETRO,           ///< retro thrusters
	THGROUP_HOVER,           ///< hover thrusters
	THGROUP_ATT_PITCHUP,     ///< rotation: pitch up
	THGROUP_ATT_PITCHDOWN,   ///< rotation: pitch down
	THGROUP_ATT_YAWLEFT,     ///< rotation: yaw left
	THGROUP_ATT_YAWRIGHT,    ///< rotation: yaw right
	THGROUP_ATT_BANKLEFT,    ///< rotation: bank left
	THGROUP_ATT_BANKRIGHT,   ///< rotation: bank right
	THGROUP_ATT_RIGHT,       ///< translation: move right
	THGROUP_ATT_LEFT,        ///< translation: move left
	THGROUP_ATT_UP,          ///< translation: move up
	THGROUP_ATT_DOWN,        ///< translation: move down
	THGROUP_ATT_FORWARD,     ///< translation: move forward
	THGROUP_ATT_BACK,        ///< translation: move back
	THGROUP_USER = 0x40,     ///< user-defined group
	THGROUP_USER_LAST = 0xFF ///< range limit for user-defined groups
};
//@}

typedef enum {
	ATTMODE_DISABLED,
	ATTMODE_ROT,
	ATTMODE_LIN,
} ATTITUDEMODE;

// ===========================================================================
/// \ingroup defines
/// \defgroup airfoilliftdir Airfoil orientation
// ===========================================================================
//@{
/**
 * \brief Lift vector orientation for airfoils.
 *
 * Defines the orientation of an airfoil by the direction of the lift vector
 * generated (vertical or horizontal).
 * \sa VESSEL::CreateAirfoil, VESSEL::CreateAirfoil2, VESSEL::CreateAirfoil3, VESSEL::CreateAirfoil4
 */
typedef enum {
	LIFT_VERTICAL,     ///< lift direction is vertical (e.g. elevator)
	LIFT_HORIZONTAL,    ///< lift direction is horizontal (e.g. rudder)
	FORCE_AND_MOMENT	///< complex model of forces and moments along and about all axes
} AIRFOIL_ORIENTATION;
//@}


// ===========================================================================
/// \ingroup defines
/// \defgroup airctrltype Aerodynamic control surface types
// ===========================================================================
//@{
/**
 * \brief Control surfaces provide attitude and drag control during
 *   atmospheric flight.
 * \sa VESSEL::CreateControlSurface, VESSEL::CreateControlSurface2, VESSEL::CreateControlSurface3
 */
typedef enum {
	AIRCTRL_ELEVATOR,     ///< elevator control (pitch control)
	AIRCTRL_RUDDER,       ///< rudder control (yaw control)
	AIRCTRL_AILERON,      ///< aileron control (bank control)
	AIRCTRL_FLAP,         ///< flaps (lift, drag control)
	AIRCTRL_ELEVATORTRIM, ///< elevator trim
	AIRCTRL_RUDDERTRIM    ///< rudder trim
} AIRCTRL_TYPE;
//@}


// ===========================================================================
/// \ingroup defines
/// \defgroup airctrlaxis Control surface axis orientation
// ===========================================================================
//@{
/**
 * \brief Constants to define the rotation axis and direction of
 *  aerodynamic control surfaces.
 * \sa VESSEL::CreateControlSurface, VESSEL::CreateControlSurface2, VESSEL::CreateControlSurface3
 */
#define AIRCTRL_AXIS_AUTO        0 ///< automatic orientation
#define AIRCTRL_AXIS_YPOS        1 ///< y-axis (vertical), positive rotation
#define AIRCTRL_AXIS_YNEG        2 ///< y-axis (vertical), negative rotation
#define AIRCTRL_AXIS_XPOS        3 ///< x-axis (transversal), positive rotation
#define AIRCTRL_AXIS_XNEG        4 ///< x-axis (transversal), negative rotation
//@}

/************************************************************************/
/**
 * \ingroup defines
 * \defgroup navmode Navigation mode identifiers
 *
 *  These constants are used to refer to the built-in "auto-navigation"
 *  modes, mostly for mainaining specific vessel attitudes via use of
 *  RCS thrusters.
 * \sa VESSEL::ActivateNavmode, VESSEL::DeactivateNavmode, VESSEL::ToggleNavmode,
 *   VESSEL::GetNavmodeState
 */
//@{
#define NAVMODE_KILLROT          1 ///< "Kill rotation" mode
#define NAVMODE_HLEVEL           2 ///< "Hold level with horizon" mode
#define NAVMODE_PROGRADE         3 ///< "Prograde" mode
#define NAVMODE_RETROGRADE       4 ///< "Retrograde" mode
#define NAVMODE_NORMAL           5 ///< "Normal to orbital plane" mode
#define NAVMODE_ANTINORMAL       6 ///< "Anti-normal to orbital plane" mode
#define NAVMODE_HOLDALT          7 ///< "Hold altitude" mode
//@}


typedef double (*LiftCoeffFunc)(double aoa); // obsolete

typedef void (*AirfoilCoeffFunc)(
	double aoa, double M, double Re,
	double *cl, double *cm, double *cd);
// Template for aerodynamic coefficients callback function
// Used to calculate lift coefficient cl, moment coefficient
// cm, and drag coefficient cd as a function of angle of attack
// aoa, Mach number M, and Reynolds number Re

typedef void (*AirfoilCoeffFuncEx)(
	VESSEL *v, double aoa, double M, double Re, void *context,
	double *cl, double *cm, double *cd);
// Extended version of aerodynamic coefficients callback function
// Contains additional parameters (calling vessel and pointer to
// user-defined data)

typedef void (*AirfoilCoeffFuncEx2)(
	VESSEL* v,
	VECTOR3 WindDir,
	double alpha, double beta, double gamma,
	double M, double Re, void* context,
	double* CA, double* CN, double* CY,
	double* Cl, double* Cm, double* Cn);
// Further extended version of aerodynamic coefficients callback function
// Contains additional parameters (calling vessel and pointer to
// user-defined data for all force and moment coefficients)

/**
 * \ingroup defines
 * \defgroup manctrl_mode Manual control mode identifiers
 *
 * Constants used to identify attitude control modes for manual input.
 * \sa VESSEL::GetManualControlLevel
 */
//@{
#define MANCTRL_ATTMODE          0 ///< current attitude mode
#define MANCTRL_REVMODE          1 ///< reverse of current attitude mode
#define MANCTRL_ROTMODE          2 ///< rotational attitude modes only
#define MANCTRL_LINMODE          3 ///< linear attitude modes only
#define MANCTRL_ANYMODE          4 ///< rotational and linear modes
//@}

/**
 * \ingroup defines
 * \defgroup manctrl_dev Manual control device identifiers
 *
 * Constants used to identify manual input devices.
 * \sa VESSEL::GetManualControlLevel
 */
 //@{
#define MANCTRL_KEYBOARD         0 ///< keyboard input
#define MANCTRL_JOYSTICK         1 ///< joystick input
#define MANCTRL_ANYDEVICE        2 ///< input from any device
//@}

enum AltitudeMode {
	ALTMODE_MEANRAD,  ///< altitude over mean radius
	ALTMODE_GROUND    ///< altitude over ground
};

#define RCS_NONE                 0 ///< None (RCS off)
#define RCS_ROT                  1 ///< Rotational mode
#define RCS_LIN                  2 ///< Linear (translational) mode

#endif
