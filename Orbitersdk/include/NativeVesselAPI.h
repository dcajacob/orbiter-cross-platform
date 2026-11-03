// Licensed under the MIT License
// Native vessel interface declarations. Runtime implementation/loader follows
// the production Vessel extraction; this header alone does not load a module.
#ifndef ORBITER_NATIVE_VESSEL_API_H
#define ORBITER_NATIVE_VESSEL_API_H
#ifdef _WIN32
#include "Orbitersdk.h"
#else
#include "OrbiterVectorMath.h"
#include "OrbiterVesselData.h"
#include "OrbiterVesselRecords.h"
#include "OrbiterSimulationData.h"
#include "OrbiterAnimationData.h"
#include "OrbiterMeshData.h"
#include "OrbiterCelestialData.h"
#include "OrbiterSdkDrawingTypes.h"
#include "OrbiterCockpitData.h"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iosfwd>
namespace oapi {class Sketchpad;}
class LightEmitter;
class PointLight;
class SpotLight;
struct VESSELPARAM;
#ifndef OAPIFUNC
#define OAPIFUNC __attribute__((visibility("default")))
#define ORBITER_NATIVE_OWNS_OAPIFUNC
#endif
#include "OrbiterGuiData.h"
#include "OrbiterLightData.h"
#include "OrbiterCameraData.h"
#include "VesselAPI.h"
OAPIFUNC OBJHANDLE oapiGetObjectByName (char *name);
OAPIFUNC OBJHANDLE oapiGetGbodyParent (OBJHANDLE hBody);
OAPIFUNC double oapiGetEmptyMass (OBJHANDLE hVessel);
OAPIFUNC double oapiGetFuelMass (OBJHANDLE hVessel);
OAPIFUNC double oapiGetMaxFuelMass (OBJHANDLE hVessel);
OAPIFUNC double oapiGetPropellantMaxMass (PROPELLANT_HANDLE ph);
OAPIFUNC double oapiGetPropellantMass (PROPELLANT_HANDLE ph);
OAPIFUNC PROPELLANT_HANDLE oapiGetPropellantHandle (OBJHANDLE hVessel, oapi::UInt32 idx);
OAPIFUNC DOCKHANDLE oapiGetDockHandle (OBJHANDLE hVessel, oapi::UInt n);
OAPIFUNC OBJHANDLE oapiGetDockStatus (DOCKHANDLE dock);
OAPIFUNC void oapiSetAutoCapture(DOCKHANDLE hDock, bool enable);
OAPIFUNC OBJHANDLE oapiGetDockOwner(DOCKHANDLE hDock);
OAPIFUNC void oapiSetEmptyMass (OBJHANDLE hVessel, double mass);
OAPIFUNC void oapiGetGlobalVel (OBJHANDLE hObj, VECTOR3 *vel);
OAPIFUNC void oapiGetFocusGlobalPos (VECTOR3 *pos);
OAPIFUNC void oapiGetFocusGlobalVel (VECTOR3 *vel);
OAPIFUNC void oapiGetRelativePos (OBJHANDLE hObj, OBJHANDLE hRef, VECTOR3 *pos);
OAPIFUNC void oapiGetRelativeVel (OBJHANDLE hObj, OBJHANDLE hRef, VECTOR3 *vel);
OAPIFUNC void oapiGetFocusRelativePos (OBJHANDLE hRef, VECTOR3 *pos);
OAPIFUNC void oapiGetFocusRelativeVel (OBJHANDLE hRef, VECTOR3 *vel);
OAPIFUNC void oapiGlobalToLocal (OBJHANDLE hObj, const VECTOR3 *glob, VECTOR3 *loc);
OAPIFUNC void oapiEquToGlobal (OBJHANDLE hObj, double lng, double lat, double rad, VECTOR3 *glob);
OAPIFUNC double oapiOrthodome (double lng1, double lat1, double lng2, double lat2);
OAPIFUNC int oapiGetAltitude (OBJHANDLE hVessel, double *alt);
OAPIFUNC int oapiGetAltitude (OBJHANDLE hVessel, AltitudeMode mode, double *alt);
OAPIFUNC int oapiGetPitch (OBJHANDLE hVessel, double *pitch);
OAPIFUNC int oapiGetBank (OBJHANDLE hVessel, double *bank);
OAPIFUNC int oapiGetHeading (OBJHANDLE hVessel, double *heading);
OAPIFUNC int oapiGetEquPos (OBJHANDLE hVessel, double *longitude, double *latitude, double *radius);
OAPIFUNC int oapiGetGroundspeed (OBJHANDLE hVessel, double *groundspeed);
OAPIFUNC bool oapiGetGroundspeedVector (OBJHANDLE hVessel, REFFRAME frame, VECTOR3 *vel);
OAPIFUNC int oapiGetAirspeed (OBJHANDLE hVessel, double *airspeed);
OAPIFUNC bool oapiGetAirspeedVector (OBJHANDLE hVessel, REFFRAME frame, VECTOR3 *vel);
OAPIFUNC void oapiGetAtm (OBJHANDLE hVessel, ATMPARAM *prm, OBJHANDLE *hAtmRef=nullptr);
OAPIFUNC VECTOR3 oapiGetGroundVector (OBJHANDLE hPlanet, double lng, double lat, int frame=2);
OAPIFUNC double oapiGetSysStep ();
OAPIFUNC double oapiGetSimMJD ();
OAPIFUNC double oapiTime2MJD (double t);
OAPIFUNC double oapiGetTimeAcceleration ();
OAPIFUNC double oapiGetPlanetPeriod (OBJHANDLE hPlanet);
OAPIFUNC void oapiGetPlanetObliquityMatrix (OBJHANDLE hPlanet, MATRIX3 *mat);
OAPIFUNC double oapiGetPlanetCurrentRotation (OBJHANDLE hPlanet);
OAPIFUNC oapi::UInt32 oapiGetPlanetJCoeffCount (OBJHANDLE hPlanet);
OAPIFUNC double oapiGetPlanetJCoeff (OBJHANDLE hPlanet, oapi::UInt32 n);
OAPIFUNC oapi::UInt32 oapiGetNavChannel (NAVHANDLE hNav);
OAPIFUNC double oapiGetNavSignal (NAVHANDLE hNav, const VECTOR3 &gpos);
OAPIFUNC float oapiGetNavRange (NAVHANDLE hNav);
OAPIFUNC int oapiGetNavDescr (NAVHANDLE hNav, char *descr, int maxlen);
OAPIFUNC void oapiOpenInputBox(char*,bool(*)(void*,char*,void*),char* = nullptr,int = 20,void* = nullptr);
OAPIFUNC void oapiOpenInputBoxEx(const char*,bool(*)(void*,char*,void*),bool(*)(void*,char*,void*),char* = nullptr,int = 20,void* = nullptr,oapi::UInt32 = 0);
OAPIFUNC double oapiGetInducedDrag(double cl,double aspect,double efficiency);
OAPIFUNC double oapiGetWaveDrag(double mach,double m1,double m2,double m3,double maximum);
OAPIFUNC OBJHANDLE oapiCreateVessel(const char*,const char*,const VESSELSTATUS&);
OAPIFUNC OBJHANDLE oapiCreateVesselEx(const char*,const char*,const void*);
OAPIFUNC bool oapiDeleteVessel(OBJHANDLE,OBJHANDLE alternative=nullptr);
OAPIFUNC OBJHANDLE oapiSetFocusObject(OBJHANDLE);
OAPIFUNC VESSEL* oapiGetFocusInterface();
OAPIFUNC OBJHANDLE oapiGetVesselByName(char*);
OAPIFUNC OBJHANDLE oapiGetVesselByIndex(int);
OAPIFUNC oapi::UInt32 oapiGetVesselCount();
OAPIFUNC void oapiOpenMFD (int mode, int mfd);
OAPIFUNC void oapiToggleMFD_on (int mfd);
OAPIFUNC int oapiRegisterMFDMode (MFDMODESPECEX &spec);
OAPIFUNC bool oapiUnregisterMFDMode (int mode);
OAPIFUNC int oapiGetMFDMode (int mfd);
OAPIFUNC double oapiSetMFDRefreshIntervalMultiplier (int mfd, double multiplier=1.0);
OAPIFUNC int oapiBroadcastMFDMessage (int mfdmode, int msg, void *data);
OAPIFUNC int oapiSendMFDKey (int mfd, oapi::UInt32 key);
OAPIFUNC void oapiRefreshMFDButtons (int mfd, OBJHANDLE hVessel);
OAPIFUNC bool oapiProcessMFDButton (int mfd, int bt, int event);
OAPIFUNC const char *oapiMFDButtonLabel (int mfd, int bt);
OAPIFUNC void oapiRegisterMFD (int mfd, const MFDSPEC &spec);
OAPIFUNC void oapiDisableMFDMode (int mode);
OAPIFUNC int oapiGetMFDModeSpecEx (char *name, MFDMODESPECEX **spec=nullptr);
OAPIFUNC void oapiVCRegisterMFD (int mfd, const VCMFDSPEC *spec);
OAPIFUNC void oapiVCRegisterHUD (const VCHUDSPEC *spec);
OAPIFUNC void oapiWriteScenario_string(FILEHANDLE,char*,char*);
#ifdef ORBITER_NATIVE_OWNS_OAPIFUNC
#undef OAPIFUNC
#undef ORBITER_NATIVE_OWNS_OAPIFUNC
#endif
#endif
#endif
