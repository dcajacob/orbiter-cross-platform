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
#include "VesselAPI.h"
#ifdef ORBITER_NATIVE_OWNS_OAPIFUNC
#undef OAPIFUNC
#undef ORBITER_NATIVE_OWNS_OAPIFUNC
#endif
#endif
#endif
