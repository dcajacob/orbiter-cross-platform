// Licensed under the MIT License
#ifndef ORBITER_SPICE_PLATFORM_H
#define ORBITER_SPICE_PLATFORM_H
#include <cstdio>
#include <cstring>
#include <cmath>
#ifdef ORBITER_NATIVE_MODULE
#include "Production/NativeCelestialApi.h"
#include "OrbiterCelestialData.h"
#include "ConfigFile.h"
using SpiceModuleBase=orbiter::native::CelestialModule;
using SpiceBodyContext=const orbiter::native::CelestialInit&;
using SpiceConfiguration=std::ifstream*;
using SpiceAtmosphere=orbiter::native::Atmosphere;
using SpiceAtmosphereParameters=orbiter::native::AtmosphereOutput;
namespace {orbiter::native::CelestialHost* spiceHost=nullptr;}
inline void SpiceLog(const char* message) {spiceHost->Log(message);}
inline bool SpiceReadString(SpiceConfiguration config,const char* key,char* value)
{return config && GetItemString(*config,key,value);}
inline bool SpiceReadReal(SpiceConfiguration config,const char* key,double& value)
{return config && GetItemReal(*config,key,value);}
inline double SpiceTimeToMJD(double seconds) {return spiceHost->TimeToMJD(seconds);}
inline std::string SpiceKernelPath(const std::string& path) {return spiceHost->Resource(path).string();}
#else
#include "Orbitersdk.h"
using SpiceModuleBase=CELBODY2;
using SpiceBodyContext=OBJHANDLE;
using SpiceConfiguration=FILEHANDLE;
using SpiceAtmosphere=ATMOSPHERE;
using SpiceAtmosphereParameters=ATMPARAM;
inline void SpiceLog(const char* message) {oapiWriteLog(const_cast<char*>(message));}
inline bool SpiceReadString(SpiceConfiguration config,const char* key,char* value)
{return oapiReadItem_string(config,const_cast<char*>(key),value);}
inline bool SpiceReadReal(SpiceConfiguration config,const char* key,double& value)
{return oapiReadItem_float(config,const_cast<char*>(key),value);}
inline double SpiceTimeToMJD(double seconds) {return oapiTime2MJD(seconds);}
inline const std::string& SpiceKernelPath(const std::string& path) {return path;}
#endif
#endif
