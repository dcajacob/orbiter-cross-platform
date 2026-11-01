// Licensed under the MIT License
#ifndef ORBITER_PRODUCTION_NAVIGATION_DATA_H
#define ORBITER_PRODUCTION_NAVIGATION_DATA_H
#include "CoreTypes.h"
#include "OrbiterHandles.h"
#ifdef _WIN32
#include "OrbiterAPI.h"
#endif
namespace orbiter::production {
#ifdef _WIN32
using NavigationData = NAVDATA;
#else
#define TRANSMITTER_NONE 0
#define TRANSMITTER_VOR  1
#define TRANSMITTER_VTOL 2
#define TRANSMITTER_ILS  3
#define TRANSMITTER_IDS  4
#define TRANSMITTER_XPDR 5
typedef struct {
	// general data
	UInt32 type;                ///< transmitter type id
	UInt32 ch;                  ///< transmitter channel (0..639)
	double power;              ///< transmitter power [arbitrary units]
	const char *descr;         ///< pointer to transmitter description string
	// type-specific data
    union {
		struct {
			OBJHANDLE hPlanet; ///< associated planet
			double lng, lat;   ///< transmitter location [rad]
		} vor;
		struct {
			OBJHANDLE hBase;   ///< associated base
			int npad;          ///< pad number (>= 0)
		} vtol;
	    struct {
			OBJHANDLE hBase;   ///< associated base
		    double appdir;     ///< ILS approach direction [rad]
	    } ils;
		struct {
			OBJHANDLE hVessel; ///< associated vessel
			DOCKHANDLE hDock;  ///< associated docking port
		} ids;
		struct {
			OBJHANDLE hVessel; ///< associated vessel
		} xpdr;
	};
} NavigationData;
#endif
}
#endif
