// Copyright (c) Martin Schweiger
// Licensed under the MIT License

#ifndef __MARSATM2006_H
#define __MARSATM2006_H

#include "../AtmospherePlatform.h"

// ======================================================================
// class MarsAtmosphere_2006
// Mars atmosphere model, as used in Orbiter 2006
// ======================================================================

class MarsAtmosphere_2006: public AtmosphereBase {
public:
	MarsAtmosphere_2006 (AtmosphereCelestial *body): AtmosphereBase (body) {}
	const char *clbkName () const;
	bool clbkConstants (AtmosphereConstants *atmc) const;
	bool clbkParams (const PRM_IN *prm_in, PRM_OUT *prm);
};

#endif // !__MARSATM2006_H