// Copyright (c) Martin Schweiger
// Licensed under the MIT License
#ifndef ORBITER_SDK_CELESTIAL_DATA_H
#define ORBITER_SDK_CELESTIAL_DATA_H

// Verbatim SDK constants, value record and flags. No platform services.

const double PI    = 3.14159265358979323846;	///< pi
const double PI05  = 1.57079632679489661923;	///< pi/2
const double PI2   = 6.28318530717958647693;	///< pi*2
const double RAD   = PI/180.0;      ///< factor to map degrees to radians
const double DEG   = 180.0/PI;      ///< factor to map radians to degrees
const double C0    = 299792458.0;   ///< speed of light in vacuum [m/s]
const double TAUA  = 499.004783806; ///< light time for 1 AU [s]
const double AU    = C0*TAUA;       ///< astronomical unit (mean geocentric distance of the sun) [m]
const double GGRAV = 6.67259e-11;   ///< gravitational constant [m^3 kg^-1 s^-2]
const double G     = 9.81;          ///< gravitational acceleration [m/s^2] at Earth mean radius
const double ATMP  = 101.4e3;       ///< atmospheric pressure [Pa] at Earth sea level
const double ATMD  = 1.293;         ///< atmospheric density [kg/m^3] at Earth sea level

/** \brief Atmospheric parameters structure */
typedef struct {
	double T;          ///<     temperature [K]
	double p;          ///<     pressure [Pa]
	double rho;        ///<     density [kg/m^3]
} ATMPARAM;

// Object types
#define OBJTP_INVALID            0
#define OBJTP_GENERIC            1
#define OBJTP_CBODY              2
#define OBJTP_STAR               3
#define OBJTP_PLANET             4
#define OBJTP_VESSEL            10
#define OBJTP_SURFBASE          20

#define EPHEM_TRUEPOS     0x01	///< true body position
#define EPHEM_TRUEVEL     0x02	///< true body velocity
#define EPHEM_BARYPOS     0x04	///< barycentric position
#define EPHEM_BARYVEL     0x08	///< barycentric velocity
#define EPHEM_BARYISTRUE  0x10	///< body has no child objects
#define EPHEM_PARENTBARY  0x20	///< ephemerides are computed in terms of the barycentre of the parent body's system
#define EPHEM_POLAR       0x40	///< data is returned in polar format

#endif
