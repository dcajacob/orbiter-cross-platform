// Copyright (c) Martin Schweiger
// Licensed under the MIT License
// Configuration loading for the original orbital-element implementation.
#include "Element.h"
#include "ConfigFile.h"

Elements::Elements(std::istream& input, double reference_mjd)
{ ReadConfiguration(input, reference_mjd); }

void Elements::ReadConfiguration(std::istream& input, double reference_mjd)
{
	double epoch;
	if (!GetItemReal (input, "Epoch", epoch))           epoch  = 2000.0;
	mjd_epoch = Jepoch2MJD (epoch);
	t_epoch   = (mjd_epoch-reference_mjd)*86400.0;
	if (!GetItemReal (input, "SemiMajorAxis", a))       a      = 1.0;
	if (!GetItemReal (input, "Eccentricity", e))        e      = 0.0;
	if (!GetItemReal (input, "Inclination", i))         i      = 0.0;
	if (!GetItemReal (input, "LongAscNode", theta))     theta  = 0.0;
	if (!GetItemReal (input, "LongPerihelion", omegab)) omegab = 0.0;
	if (!GetItemReal (input, "MeanLongitude", L))       L      = 0.0;
}
