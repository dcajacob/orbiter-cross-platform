// Licensed under the MIT License
// Internal source-built module API. This is not the Windows binary SDK.
#ifndef ORBITER_NATIVE_CELESTIAL_API_H
#define ORBITER_NATIVE_CELESTIAL_API_H
#include "Export.h"
#include "NativeModule.h"
#include "OrbiterVector.h"
#include "OrbiterCelestialData.h"
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <memory>
#include <string>
class CelestialBody;
namespace orbiter::native {
class CelestialModule;
class Atmosphere;
// Field meanings and units are the original production ATMCONST/ATMOSPHERE
// data contract. Windows SDK declarations remain in their original header.
struct AtmosphereConstants {
    double p0,rho0,R,gamma,C,O2pp,altlimit,radlimit,horizonalt;
    VECTOR3 color0;
};
struct AtmosphereInput {
    double alt,lng,lat,f107bar,f107,ap;
    std::uint32_t flag;
};
struct AtmosphereOutput {double T,p,rho;};
class CelestialHost {
public:
    virtual ~CelestialHost()=default;
    virtual void Log(const std::string&)=0;
    virtual double SimulationMJD() const=0;
    virtual double TimeToMJD(double seconds) const=0;
    virtual std::filesystem::path Resource(const std::string&) const=0;
    virtual double RotationPeriod(const CelestialBody&) const=0;
    virtual VECTOR3 GlobalPosition(const CelestialBody&) const=0;
    virtual void GlobalToEquatorial(const CelestialBody&,const VECTOR3&,double&,double&,double&) const=0;
    virtual std::string AtmosphereSelection(const CelestialBody&,std::ifstream&) const=0;
    virtual std::unique_ptr<production::NativeModule> LoadAtmosphere(CelestialModule&,const char* name)=0;
};
struct CelestialInit {
    std::uint32_t size=sizeof(CelestialInit);
    CelestialBody* body=nullptr;
    CelestialHost* host=nullptr;
};
class ORBITER_PRODUCTION_API CelestialModule {
public:
    explicit CelestialModule(const CelestialInit&);
    virtual ~CelestialModule();
    CelestialModule(const CelestialModule&)=delete;
    CelestialModule& operator=(const CelestialModule&)=delete;
    virtual bool bEphemeris() const=0;
    virtual void clbkInit(std::ifstream* config);
    virtual int clbkEphemeris(double mjd,int request,double* result)=0;
    virtual int clbkFastEphemeris(double seconds,int request,double* result)=0;
    virtual bool clbkAtmParam(double altitude,AtmosphereOutput* result)=0;
    CelestialBody* GetHandle() const {return context.body;}
    Atmosphere* GetAtmosphere() const {return atm;}
    double SidRotPeriod() const;
    CelestialHost& Host() const {return *context.host;}
protected:
    bool LoadAtmosphereModule(const char* name);
    short version=2;
    Atmosphere* atm=nullptr;
private:
    CelestialInit context;
    std::unique_ptr<production::NativeModule> atmosphere;
};
class ORBITER_PRODUCTION_API Atmosphere {
public:
    explicit Atmosphere(CelestialModule* body);
    virtual ~Atmosphere()=default;
    using PRM_IN=AtmosphereInput;
    using PRM_OUT=AtmosphereOutput;
    enum PRM_IN_FLAG {PRM_ALT=0x0001,PRM_LNG=0x0002,PRM_LAT=0x0004,PRM_FBR=0x0008,PRM_F=0x0010,PRM_AP=0x0020};
    virtual const char* clbkName() const=0;
    virtual bool clbkConstants(AtmosphereConstants*) const;
    virtual bool clbkParams(const PRM_IN*,PRM_OUT*)=0;
protected:
    CelestialModule* cbody;
};
}
#endif
