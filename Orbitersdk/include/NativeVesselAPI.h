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
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iosfwd>
namespace oapi {class Sketchpad;}
class LightEmitter;
class PointLight;
class SpotLight;
struct MFDSPEC;
struct VCMFDSPEC;
struct VCHUDSPEC;
struct HUDPAINTSPEC;
struct MFDMODESPEC;
struct MFDMODESPECEX;
struct HUDPARAM;
struct VESSELPARAM;
#ifndef OAPIFUNC
#define OAPIFUNC __attribute__((visibility("default")))
#define ORBITER_NATIVE_OWNS_OAPIFUNC
#endif
#include "OrbiterLightData.h"
#include "OrbiterCameraData.h"
#include "VesselAPI.h"
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
#ifdef ORBITER_NATIVE_OWNS_OAPIFUNC
#undef OAPIFUNC
#undef ORBITER_NATIVE_OWNS_OAPIFUNC
#endif
#endif
#endif
