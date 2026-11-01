// Copyright (c) Martin Schweiger and Orbiter contributors
// Licensed under the MIT License
#include "Celbody.h"
#include "Element.h"
#include "ConfigFile.h"
#include "Production/RigidBodyServices.h"
#include "Production/Text.h"
#include <fstream>
#include <cstring>
#include <cstdio>
#include <stdexcept>
using namespace std;
using namespace orbiter::production;

CelestialBody::CelestialBody (char *fname)
: RigidBody (fname), pinesgrav(this)
{
	char cbuf[512];
	int gravcoeff = 0;
	usePinesGravity = false;

	DefaultParam ();
	ClearModule ();

	try {
	ifstream ifs (GetBodyServices().ConfigPath(fname));
	if (!ifs) {
		GetCelestialServices().ConfigFailure(GetBodyServices().ConfigPath(fname));
		throw std::runtime_error("Celestial configuration could not be opened");
	}

	if (GetItemString (ifs, "Module", cbuf))
		RegisterModule (cbuf);

	GetItemReal (ifs, "SidRotPeriod", rot_T);
	GetItemReal (ifs, "SidRotOffset", Dphi);
	GetItemReal (ifs, "Obliquity", eps_rel);
	GetItemReal (ifs, "LAN", Lrel0);
	GetItemReal (ifs, "LAN_MJD", mjd_rel);
	GetItemReal (ifs, "PrecessionPeriod", prec_T);

	// precession parameters
	GetItemReal (ifs, "PrecessionObliquity", eps_ref);
	GetItemReal (ifs, "PrecessionLAN", lan_ref);

	if (GetItemString(ifs, "GravModelPath", cbuf) && GetItemInt(ifs, "GravCoeffCutoff", gravcoeff)) {
		const auto gravityPath = GetCelestialServices().GravityModelPath(cbuf);
		const auto gravityName = gravityPath.string();
		int maxGravityTerms = 0, actualLoadedTerms = 0;
		const int readResult = pinesgrav.ReadGravityModel(gravityPath, gravcoeff, actualLoadedTerms, maxGravityTerms);
		if (readResult == 0) {
			GetCelestialServices().Log("GRAVITY MODEL: "+gravityName+" LOADED, Terms "+
				std::to_string(actualLoadedTerms)+"/"+std::to_string(maxGravityTerms));
		} else {
			const char* prefix[] = {"", "COEFFICIENT FILE ", "COULD NOT ALLOCATE SPACE FOR GRAVITY MODEL ",
				"BAD HEADDER LINE FORMAT ", "BAD COEFFICIENT LINE FORMAT "};
			GetCelestialServices().Log(std::string("GRAVITY MODEL ERROR: ")+prefix[readResult]+gravityName+
				(readResult == 1 ? " NOT FOUND" : ""));
		}

		if (readResult && GetCelestialServices().RequireGravityModel())
			throw std::runtime_error("Required gravity model could not be loaded: "+gravityName);
		if (readResult == 0) {
			usePinesGravity = true;
		}
	}

	if (GetItemString (ifs, "JCoeff", cbuf)) {
		char *str;
		str = strtok (cbuf, " \t");
		while (str) {
			double *tmp = new double[njcoeff+1]; GetRigidBodyServices().TraceAllocation(__FILE__,__LINE__);
			if (njcoeff) {
				memcpy (tmp, jcoeff, njcoeff*sizeof(double));
				delete []jcoeff;
			}
			jcoeff = tmp;
			sscanf (str, "%lf", jcoeff + njcoeff++);
			str = strtok (NULL, " \t");
		}
	}

	if (GetItemBool (ifs, "HasElements", bInitFromElements) && bInitFromElements) {
		if (GetItemString (ifs, "ElReference", cbuf) &&
			!ComparePrefix(cbuf, "ParentEquator", sizeof("ParentEquator")))
			elframe = ELFRAME_PARENTEQU;
		std::ifstream elementsFile(GetBodyServices().ConfigPath(fname));
		el = new Elements(elementsFile, CelestialClock().MJD_ref); GetRigidBodyServices().TraceAllocation(__FILE__,__LINE__);
	}

	double prec;
	if (modIntf.oplanetSetPrecision && GetItemReal (ifs, "ErrorLimit", prec))
		modIntf.oplanetSetPrecision (prec); // old-style initialisation - OBSOLETE

	GetItemBool (ifs, "EllipticOrbit", bFixedElements);
	bDynamicPosVel = !bFixedElements;

	if (GetCelestialServices().HasModule(*this)) {
		GetCelestialServices().InitializeModule(*this, ifs);
		if (GetCelestialServices().HasEphemeris(*this)) { // ephemerides calculated by module
			bDynamicPosVel = false;
			bFixedElements = false;
		}
	}
	if (modIntf.oplanetEphemeris) { // old module interface
		bDynamicPosVel = false;
		bFixedElements = false;
	}

	if (!el) { el = new Elements(CelestialClock().MJD_ref); GetRigidBodyServices().TraceAllocation(__FILE__,__LINE__); }

	Dphi += (CelestialClock().MJD0 - el->MJDepoch()) * (86400.0/rot_T)*Pi2; // merge rotation at t=0 into offset
	Dphi += Lrel0*cos(eps_rel); // merge precession state into offset
	Dphi = fmod (Dphi, Pi2);
	} catch (...) {
		ClearModule();
		if (njcoeff) { delete[] jcoeff; jcoeff=nullptr; njcoeff=0; }
		throw;
	}
}

