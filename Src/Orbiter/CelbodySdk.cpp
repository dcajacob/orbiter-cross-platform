// Copyright (c) Martin Schweiger
// Licensed under the MIT License
#define OAPI_IMPLEMENTATION
#include "Orbiter.h"
#include "Celbody.h"
#include "Orbitersdk.h"
extern Orbiter* g_pOrbiter;
using namespace std;
void Pol2Crt(double*, double*, bool, bool);

// =======================================================================
// Class CELBODY: API interface class

CELBODY::CELBODY ()
{ version = 1; }

bool CELBODY::bEphemeris () const
{ return false; }

void CELBODY::clbkInit (FILEHANDLE cfg)
{}

int CELBODY::clbkEphemeris (double mjd, int req, double *ret)
{ return 0; }

int CELBODY::clbkFastEphemeris (double simt, int req, double *ret)
{ return 0; }

bool CELBODY::clbkAtmParam (double alt, ATMPARAM *prm)
{ return false; }

void CELBODY::Pol2Crt (double *pol, double *crt)
{
	::Pol2Crt (pol, crt, true, true);
}


// =======================================================================
// class CELBODY2: API interface class

CELBODY2::CELBODY2 (OBJHANDLE hCBody): CELBODY ()
{
	version++;
	hBody = hCBody;
	atm = NULL;
	hAtmModule = NULL;
}

CELBODY2::~CELBODY2 ()
{
	FreeAtmosphere();
}

void CELBODY2::clbkInit (FILEHANDLE cfg)
{
	CELBODY::clbkInit (cfg);

	// Load external atmosphere modules
	if (!hAtmModule) {
		// 1: try Config\<Name>\Atmosphere.cfg for interactive setting
		char fname[256], name[256];
		oapiGetObjectName (hBody, name, 256);
		strcat (name, "\\Atmosphere.cfg");
		FILEHANDLE hFile = oapiOpenFile (name, FILE_IN, CONFIG);
		if (oapiReadItem_string (hFile, (char*)"MODULE_ATM", fname) || oapiReadItem_string (cfg, (char*)"MODULE_ATM", fname)) {
			if (_stricmp (fname, "[None]"))
				LoadAtmosphereModule (fname);
		}
		oapiCloseFile (hFile, FILE_IN);
	}
}

OBJHANDLE CELBODY2::GetParent () const
{
	return (OBJHANDLE)((CelestialBody*)hBody)->cbody;
}

OBJHANDLE CELBODY2::GetChild (DWORD idx) const
{
	CelestialBody *cbody = (CelestialBody*)hBody;
	if (idx < cbody->nsecondary) return (OBJHANDLE)cbody->secondary[idx];
	else                         return NULL;
}

void CELBODY2::SetAtmosphere (ATMOSPHERE *a)
{
	FreeAtmosphere(); // unload existing atmosphere instance
	atm = a;
}

bool CELBODY2::FreeAtmosphere ()
{
	if (!atm) return false;
	if (!FreeAtmosphereModule()) {
		delete atm;
		atm = 0;
	}
	return true;
}

bool CELBODY2::LoadAtmosphereModule (const char *fname)
{
	char path[256], name[256];
	oapiGetObjectName (hBody, name, 256);
	sprintf (path, "Modules\\Celbody\\%s\\Atmosphere", name);
	if (!(hAtmModule = g_pOrbiter->LoadModule (path, fname))) return false;
	ATMOSPHERE *(*func)(CELBODY2*) = (ATMOSPHERE*(*)(CELBODY2*))GetProcAddress (hAtmModule, "CreateAtmosphere");
	if (!func) {
		g_pOrbiter->UnloadModule (fname);
		hAtmModule = NULL;
		return false;
	}
	atm = func(this);
	return true;
}

bool CELBODY2::FreeAtmosphereModule ()
{
	if (!hAtmModule) return false;
	if (atm) {
		void (*func)(ATMOSPHERE*) = (void(*)(ATMOSPHERE*))GetProcAddress(hAtmModule, "DeleteAtmosphere");
		if (func) {
			func (atm);
		} else {
			// no instance destruction support in module - let's do it ourselves
			delete atm;
		}
		atm = 0;
	}
	g_pOrbiter->UnloadModule (hAtmModule);
	hAtmModule = NULL;
	return true;
}

double CELBODY2::SidRotPeriod () const
{
	return ((CelestialBody*)hBody)->rot_T;
}


// =======================================================================
// class ATMOSPHERE: API interface class

ATMOSPHERE::ATMOSPHERE (CELBODY2 *body)
{
	cbody =  body;
}

bool ATMOSPHERE::clbkConstants (ATMCONST *atmc) const
{
	// Some Earth defaults. Probably not very useful in general, but
	// we want to make sure they are set to physical values.
	atmc->R = 286.91;
	atmc->gamma = 1.4;
	return false;
}

bool ATMOSPHERE::clbkParams (const PRM_IN *prm_in, PRM_OUT *prm_out)
{
	return false;
}

