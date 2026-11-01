// Copyright (c) Martin Schweiger
// Licensed under the MIT License
#ifndef ORBITER_ASTRO_MATH_H
#define ORBITER_ASTRO_MATH_H

// Original engine constants/conversions, independent of SDK/platform services.
const double Ggrav = 6.67259e-11;
const double MJD2000 = 51544.5;
const double day = (1.0/86400.0);

inline double Day(double sec) { return sec * day; }
inline double Jepoch2MJD(double J) { return (J-2000.0)*365.25 + MJD2000; }
inline double MJD2Jepoch(double mjd) { return 2000.0 + (mjd-MJD2000)/365.25; }

inline double E_grav (double M, double d2)
{ return Ggrav * M / d2; }
// magnitude of gravitation field strength caused by mass M at distance d,
// where d2 = d*d

#endif
