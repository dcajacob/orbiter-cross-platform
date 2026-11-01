// Copyright (c) Martin Schweiger and Orbiter contributors
// Licensed under the MIT License
#include "WindowsCelestialServices.h"
#include "Celbody.h"
#include "Orbiter.h"
#include "Log.h"
#include <cstring>
#include <type_traits>
extern Orbiter* g_pOrbiter;
using namespace std;
namespace orbiter::production {
static_assert(std::is_same<UInt32,DWORD>::value, "Celestial SDK scalar type changed");
class WindowsCelestialServices final : public CelestialServices {
public:
    void RegisterModule(CelestialBody& body, const char* dllname) override
    {
        auto& module=body.module; auto& modIntf=body.modIntf;
        auto& hMod=body.hMod; auto& name=body.name;

	char cbuf[256];
	module = 0;                              // reset new interface
	memset (&modIntf, 0, sizeof (modIntf));  // reset old interface
	sprintf (cbuf, "Modules\\Celbody\\%s.dll", dllname); // try new module location
	hMod = LoadLibrary (cbuf);
	if (!hMod) {
		sprintf (cbuf, "Modules\\%s.dll", dllname);  // try legacy module location
		hMod = LoadLibrary (cbuf);
	}
	if (!hMod) {
		// A body whose module cannot be loaded falls back to its config elements, or, if it has none, to a
		// dynamic integration from a zero relative state; both are wrong silently, so the failure is logged
		// with the meaning of the two usual causes: a DLL built for the other architecture, and a DLL whose
		// runtime library (for example an older Visual C++ redistributable) is not installed.
		const DWORD err = GetLastError();
		const char *hint = (err == ERROR_BAD_EXE_FORMAT) ? ": the DLL was built for a different architecture than this Orbiter" :
		                   (err == ERROR_MOD_NOT_FOUND)  ? ": the DLL or one of its dependencies, such as a runtime library it was built against, is missing" : "";
		LOGOUT_WARN("Celestial body %s: ephemeris module %s.dll could not be loaded (Windows error %lu%s); the body falls back to the orbital elements in its config file, if it has any", name.c_str(), dllname, err, hint);
		return;
	}

	// Check if the module provides instance initialisation
	typedef CELBODY* (*INITPROC)(OBJHANDLE);
	INITPROC init_proc = (INITPROC)GetProcAddress (static_cast<HMODULE>(hMod), "InitInstance");
	if (init_proc) { // load interface class

		module = init_proc ((OBJHANDLE)&body);

	} else {         // check for old-style interface
		string funcname;

		funcname = name + "_SetPrecision";
		modIntf.oplanetSetPrecision = (OPLANET_SetPrecision)GetProcAddress (static_cast<HMODULE>(hMod), funcname.c_str());

		funcname = name + "_Ephemeris";
		modIntf.oplanetEphemeris = (OPLANET_Ephemeris)GetProcAddress (static_cast<HMODULE>(hMod), funcname.c_str());

		funcname = name + "_FastEphemeris";
		modIntf.oplanetFastEphemeris = (OPLANET_FastEphemeris)GetProcAddress (static_cast<HMODULE>(hMod), funcname.c_str());

		funcname = name + "_AtmPrm";
		modIntf.oplanetAtmPrm = (OPLANET_AtmPrm)GetProcAddress (static_cast<HMODULE>(hMod), funcname.c_str());
	}

    }
    void ClearModule(CelestialBody& body) override
    {
        auto& module=body.module; auto& modIntf=body.modIntf; auto& hMod=body.hMod;

	if (hMod) {
		if (module) { // new interface
			typedef void (*EXITPROC)(CELBODY*);
			EXITPROC exit_proc = (EXITPROC)GetProcAddress (static_cast<HMODULE>(hMod), "ExitInstance");
			if (exit_proc) { // allow module to clean up
				exit_proc (module);
			} else {         // no cleanup - we delete the interface class here
				delete module;
			}
			module = 0;
		}
		FreeLibrary (static_cast<HMODULE>(hMod));
		hMod = 0;
	}
	memset (&modIntf, 0, sizeof (modIntf)); // old interface

    }
    bool HasModule(const CelestialBody& body) const override { return body.module!=nullptr; }
    void InitializeModule(CelestialBody& body, std::ifstream& input) override
    { body.module->clbkInit((FILEHANDLE)&input); }
    bool HasEphemeris(const CelestialBody& body) const override { return body.module->bEphemeris(); }
    int Ephemeris(const CelestialBody& body, double mjd, int request, double* result) const override
    { return body.module->clbkEphemeris(mjd,request,result); }
    int FastEphemeris(const CelestialBody& body, double seconds, int request, double* result) const override
    { return body.module->clbkFastEphemeris(seconds,request,result); }
    int AtmosphereModel(const CelestialBody& body,ATMCONST& atm) const override {
        auto* module=body.module; const auto& modIntf=body.modIntf;
        if (module) {
            ATMPARAM prm;
            if (module->Version()>=2 && !((CELBODY2*)module)->LegacyAtmosphereInterface()) {
                if (auto* atmosphere=((CELBODY2*)module)->GetAtmosphere()) {
                    atmosphere->clbkConstants(&atm);return 4;
                }
            } else if (module->clbkAtmParam(0,&prm)) {
                atm.p0=prm.p;atm.rho0=prm.rho;return 3;
            } else if (modIntf.oplanetAtmPrm) {
                modIntf.oplanetAtmPrm(0,&prm);
                atm.p0=prm.p;atm.rho0=prm.rho;return 2;
            }
        }
        return 0;
    }
    void AtmosphereParameters(const CelestialBody& body,int model,double alt,double lng,double lat,ATMPARAM& result) const override {
        if (model==2) body.modIntf.oplanetAtmPrm(alt,&result);
        else if (model==3) body.module->clbkAtmParam(alt,&result);
        else {
            ATMOSPHERE::PRM_IN input; ATMOSPHERE::PRM_OUT output;
            input.alt=alt;input.lng=lng;input.lat=lat;
            input.flag=ATMOSPHERE::PRM_ALT|ATMOSPHERE::PRM_LNG|ATMOSPHERE::PRM_LAT;
            ((CELBODY2*)body.module)->GetAtmosphere()->clbkParams(&input,&output);
            result.p=output.p;result.rho=output.rho;result.T=output.T;
        }
    }
    std::filesystem::path GravityModelPath(const char* name) const override
    { return std::string("GravityModels\\")+name; }
    void ConfigFailure(const std::filesystem::path& path) override
    {
        LOGOUT_ERR_FILENOTFOUND_MSG(path.string().c_str(), "while initialising celestial body");
        g_pOrbiter->TerminateOnError();
    }
    bool RequireGravityModel() const override { return false; } // Retain the Windows legacy logged fallback.
    void Log(const std::string& message) override { LOGOUT("%s",message.c_str()); }
};
CelestialServices& GetWindowsCelestialServices()
{ static WindowsCelestialServices services; return services; }
}
