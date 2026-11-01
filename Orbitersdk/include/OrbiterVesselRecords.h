// Copyright (c) Martin Schweiger
// Licensed under the MIT License
#ifndef ORBITER_VESSEL_RECORDS_H
#define ORBITER_VESSEL_RECORDS_H
#include "OrbiterValueTypes.h"
#include "OrbiterGeometry.h"
#include "OrbiterHandles.h"

/**
 * \brief Engine exhaust render parameters
 * \sa VESSEL::AddExhaust(EXHAUSTSPEC*)
 */
typedef struct {
	THRUSTER_HANDLE th;///<  handle of associated thruster (or NULL if none)
	double *level;     ///<  pointer to variable containing exhaust level (0..1)
	VECTOR3 *lpos;     ///<  pointer to exhaust position vector [m]
	VECTOR3 *ldir;     ///<  pointer to engine thrust direction (=negative exhaust direction)
	double lsize;      ///<  exhaust length [m]
	double wsize;      ///<  exhaust width [m]
	double lofs;       ///<  longitudinal offset from engine [m]
	double modulate;   ///<  magnitude of random intensity variations (0..1)
	SURFHANDLE tex;    ///<  custom texture handle
	oapi::UInt32 flags;       ///<  Bit flags (see \ref exhaustflag)
	oapi::UInt id;           ///<  reserved
} EXHAUSTSPEC;

/**
 * \brief Particle stream parameters
 * \note The following mapping methods (LEVELMAP) between stream
 *   level L and opacity a are supported:
 *   - LVL_FLAT: \f$ \alpha = \mathrm{const} \f$
 *   - LVL_LIN:  \f$ \alpha = L \f$
 *   - LVL_SQRT: \f$ \alpha = \sqrt(L) \f$
 *   - LVL_PLIN: \f$ \alpha = \left\lbrace \begin{array}{ll}
                     0 & \mathrm{if} L < L_\mathrm{min} \\
					 \frac{L-L_\mathrm{min}}{L_\mathrm{max}-L_\mathrm{min}} & \mathrm{if} L_\mathrm{min} \leq L \leq L_\mathrm{max} \\
					 1 & \mathrm{if} L > L_\mathrm{max}
					 \end{array} \right. \f$
 *   - LVL_PSQRT: \f$ \alpha = \left\lbrace \begin{array}{ll}
                     0 & \mathrm{if} L < L_\mathrm{min} \\
					 \sqrt{\frac{L-L_\mathrm{min}}{L_\mathrm{max}-L_\mathrm{min}}} & \mathrm{if} L_\mathrm{min} \leq L \leq L_\mathrm{max} \\
					 1 & \mathrm{if} L > L_\mathrm{max}
					 \end{array} \right. \f$
 */
typedef struct {
	oapi::UInt32 flags;       ///<     streamspec bitflags
	double srcsize;    ///<     particle size at creation [m]
	double srcrate;    ///<     average particle creation rate [Hz]
	double v0;         ///<     emission velocity [m/s]
	double srcspread;  ///<     velocity spread during creation
	double lifetime;   ///<     average particle lifetime [s]
	double growthrate; ///<     particle growth rate [m/s]
	double atmslowdown;///<     slowdown rate in atmosphere
	/** \brief Particle lighting method */
	enum LTYPE {
		EMISSIVE,      ///<     emissive lighting (example: plasma stream)
		DIFFUSE        ///<     diffuse lighting (example: vapour stream)
	} ltype;           ///<     render lighting method
	/** \brief Mapping from level to alpha value (particle opacity) */
	enum LEVELMAP {
		LVL_FLAT,      ///<     constant (alpha independent of level)
		LVL_LIN,       ///<     linear mapping (alpha = level)
		LVL_SQRT,      ///<     square root mapping (alpha = sqrt(level)
		LVL_PLIN,      ///<     linear mapping in sub-range
		LVL_PSQRT      ///<     square-root mapping in sub-range
	} levelmap;        ///< mapping from level to alpha
	double lmin, lmax; ///<     min and max levels for level PLIN and PSQRT mapping types
	enum ATMSMAP { ATM_FLAT, ATM_PLIN, ATM_PLOG } atmsmap;    ///< mapping from atmospheric params to alpha
	double amin, amax; ///<     min and max densities for atms PLIN mapping
	SURFHANDLE tex;    ///<     particle texture handle (NULL for default)
} PARTICLESTREAMSPEC;

/** \brief vessel beacon light parameters */
typedef struct {
	oapi::UInt32 shape;       ///<   beacon shape identifier (see \ref beaconshape)
	VECTOR3 *pos;      ///<   pointer to position in vessel coordinates
	VECTOR3 *col;      ///<   pointer to beacon RGB colour
	double size;       ///<   beacon radius
	double falloff;    ///<   distance falloff parameter
	double period;     ///<   strobe period (0 for continuous)
	double duration;   ///<   strobe duration
	double tofs;       ///<   strobe time offset
	bool active;       ///<   beacon lit?
} BEACONLIGHTSPEC;

/**
 * \brief Vessel status parameters (version 1)
 *
 * Defines vessel status parameters at a given time. This is version 1 of
 * the vessel status interface. It is retained for backward compatibility,
 * but new modules should use VESSELSTATUS2 instead to exploit the latest
 * vessel capabilities such as individual thruster and propellant resource
 * settings.
 */
typedef struct {
	/// position relative to rbody in ecliptic frame [<b>m</b>]
	VECTOR3 rpos;

	/// velocity relative to rbody in ecliptic frame [<b>m/s</b>]
	VECTOR3 rvel;

	/**
	 * \brief rotation velocity about principal axes in ecliptic frame [<b>rad/s</b>]
     * \note For a vessel with LANDED status, vrot has a different interpretation:
	 *   vrot.x contains the altitude of the CoG above the (elevated) surface. vrot.y
	 *   and vrot.z are ignored.
	 */
	VECTOR3 vrot;

	/**
	 * \brief vessel orientation against ecliptic frame (freeflight) or against
	 *   planet frame (landed)
     */
	VECTOR3 arot;

	/// fuel level [0..1]
	double fuel;

	/// main/retro engine setting [-1..1]
	double eng_main;

	/// hover engine setting [0..1]
	double eng_hovr;

	/// handle of reference body
	OBJHANDLE rbody;

    /// handle of docking or landing target
	OBJHANDLE base;

    /// index of designated docking or landing port
	int port;

    /// \brief flight status indicator
	/// \note
	/// - 0=active (freeflight)
	/// - 1=inactive (landed)
	int status;

	/// \brief additional vector parameters
	/// \note
	/// - vdata[0]: contains landing paramters if status == 1:
	///   vdata[0].x = longitude, vdata[0].y = latitude, vdata[0].z = heading of landed vessel
	/// - vdata[1] - vdata[9]: not used
	VECTOR3 vdata[10];

	/// additional floating point parameters (not used)
	double  fdata[10];

	/// \brief additional integer and bitflag parameters
	///
	/// \par flag[0]&1:
	///   - 0: ingore eng_main and eng_hovr entries, do not change thruster settings
	///   - 1: set THGROUP_MAIN and THGROUP_RETRO thruster groups from eng_main, and THGROUP_HOVER from eng_hovr.
	/// \par flag[0]&2:
	///   - 0: ignore fuel level, do not change fuel levels
	///   - 1: set fuel level of first propellant resource from fuel
	/// \note flag[1] - flag[9]: not used
	oapi::UInt32   flag[10];
} VESSELSTATUS;

/**
 * \brief Vessel status parameters (version 2)
 * \details Defines vessel status parameters at a given time. This is version 2 of
 * the vessel status interface and replaces the earlier VESSELSTATUS
 * structure. Functions using VESSELSTATUS are still supported for backward
 * compatibility. \n
 * \note The version specification is an input parameter for all function calls
 *  (including GetStatus) and must be set by the user to tell Orbiter which interface to use.
 * \sa VESSEL::GetStatusEx 
 */
typedef struct {
	/// interface version identifier (2)
	oapi::UInt32 version;

	/**
	* \brief bit flags
	* \details The meaning of the bitflags in flag depends on whether the VESSELSTATUS2
	*  structure is used to get (GetStatus) or set (SetStatus) a vessel status. The
	*  following flags are currently defined:
	* \par flags:
	* - \c VS_FUELRESET
	*		- Get - not used
	*		- Set - reset all fuel levels to zero, independent of the fuel list.
	*		.
	* - \c VS_FUELLIST
	*		- Get - request a list of current fuel levels in fuel. The module is responsible
	*		  for deleting the list after use.
	*		- Set - set fuel levels for all resources listed in fuel.
	*		.
	* - \c VS_THRUSTRESET
	*		- Get - not used
	*		- Set - reset all thruster levels to zero, independent of the thruster list
	*		.
	* - \c VS_THRUSTLIST
	*		- Get - request a list of current thrust levels in thruster. The module is
	*		   responsible for deleting the list after use.
	*		- Set - set thrust levels for all thrusters listed in thruster.
	*		.
	* - \c VS_DOCKINFOLIST
	*		- Get - request a docking port status list in dockinfo. The module is
	*		  responsible for deleting the list after use.
	*		- Set - initialise docking status for all docking ports in dockinfo.
	* \sa VESSEL::GetStatusEx 
	*/
	oapi::UInt32 flag;

	/// handle of reference body
	OBJHANDLE rbody;

	/// handle of docking or landing target
	OBJHANDLE base;

	/// index of designated docking or landing port
	int port;

	/// \brief flight status indicator
	/// \note
	/// - 0=active (freeflight)
	/// - 1=inactive (landed)
	int status;

	/// position relative to reference body (rbody) in ecliptic frame [<b>m</b>]
	VECTOR3 rpos;

	/// velocity relative to reference body in ecliptic frame [<b>m/s</b>]
	VECTOR3 rvel;

	/**
	 * \brief angular velocity around principal axes in ecliptic frame [<b>rad/s</b>]
     * \note For a vessel with LANDED status, vrot has a different interpretation:
	 *   vrot.x contains the altitude of the CoG above the (elevated) surface. vrot.y
	 *   and vrot.z are ignored.
	 */
	VECTOR3 vrot;

	/**
	* \brief vessel orientation against ecliptic frame
	* \details \b arot (\f$ \alpha, \beta, \gamma \f$) contains angles of rotation [rad] 
	*  around \e x, \e y, \e z axes in ecliptic
	*  frame to produce this rotation matrix \b R for mapping from the vessel's local
	*  frame of reference to the global frame of reference:
	* \f[ R = 
	*	\left[ \begin{array}{ccc} 1 & 0 & 0 \\	0 & \cos\alpha & \sin\alpha \\ 0 & -\sin\alpha & \cos\alpha \end{array} \right]
	*	\left[ \begin{array}{ccc} \cos\beta & 0 & -\sin\beta \\ 0 & 1 & 0 \\ \sin\beta & 0 & \cos\beta \end{array} \right]
	*	\left[ \begin{array}{ccc} \cos\gamma & \sin\gamma & 0 \\ -\sin\gamma & \cos\gamma & 0 \\ 0 & 0 & 1 \end{array} \right]	 
	* \f]
	* such that \b r<sub>global</sub> = \b R \b r<sub>local</sub> + \b p \n
	* where \b p is the vessel's global position.
	* \note For a vessel with LANDED status, arot has a different interpretation:
	*   It represents the rotation against the planet frame rather than the ecliptic frame. While the
	*   vessel is landed (idle), these values will not change over time.
	*/
	VECTOR3 arot;

	/**
	 * \brief longitude of vessel position in equatorial coordinates of rbody [rad]
	 * \note currently only defined if the vessel is landed (status=1)
	 */
	double surf_lng;

    /**
	 * \brief latitude of vessel position in equatorial coordinates of rbody [rad]
	 * \note currently only defined if the vessel is landed (status=1)
	 */
	double surf_lat;

	/**
	 * \brief vessel heading on the ground [rad]
	 * \note currently only defined if the vessel is landed (status=1)
	 */
	double surf_hdg;

	/// number of entries in the fuel list
	oapi::UInt32 nfuel;

	/// propellant list
	struct FUELSPEC {
		oapi::UInt32 idx;      ///< propellant index
		double level;   ///< propellant level
	} *fuel;

	/// number of entries in the thruster list
	oapi::UInt32 nthruster;

	/// thruster definition list
	struct THRUSTSPEC {
		oapi::UInt32 idx;      ///< thruster index 
		double level;   ///< thruster level
	} *thruster;

	/// number of entries in the dockinfo list
	oapi::UInt32 ndockinfo;

	/// dock info list
	struct DOCKINFOSPEC {
		oapi::UInt32 idx;      ///< docking port index
		oapi::UInt32 ridx;     ///< docking port index of docked vessel
		OBJHANDLE rvessel; ///< docked vessel
	} *dockinfo;

	/// transponder channel [0...640]
	oapi::UInt32 xpdr;
} VESSELSTATUS2;


// VESSELSTATUSx bitflags
#define VS_FUELRESET    0x00000001 ///< set all propellant levels to zero
#define VS_FUELLIST     0x00000002 ///< list of propellant levels is provided
#define VS_THRUSTRESET  0x00000004 ///< set all thruster levels to zero
#define VS_THRUSTLIST   0x00000008 ///< list of thruster levels is provided
#define VS_DOCKINFOLIST 0x00000010 ///< list of docked objects is provided

#endif
