// Copyright (c) Martin Schweiger
// Licensed under the MIT License

#ifndef __EARTHATM2006_H
#define __EARTHATM2006_H

#include "../AtmospherePlatform.h"

// ======================================================================
// class EarthAtmosphere_2006
// Legacy atmospheric model
// ======================================================================

class EarthAtmosphere_2006: public AtmosphereBase {
public:
	EarthAtmosphere_2006 (AtmosphereCelestial *body): AtmosphereBase (body) {}
	const char *clbkName () const;
	bool clbkConstants (AtmosphereConstants *atmc) const;
	bool clbkParams (const PRM_IN *prm_in, PRM_OUT *prm);
};

#endif // !__EARTHATM2006_H