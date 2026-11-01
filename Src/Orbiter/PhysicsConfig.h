// Copyright (c) Martin Schweiger
// Licensed under the MIT License
#ifndef ORBITER_PHYSICS_CONFIG_H
#define ORBITER_PHYSICS_CONFIG_H

// dynamic state propagation methods
#define MAX_PROP_LEVEL  5
#define MAX_APROP_LEVEL 5
#define NPROP_METHOD   10
#define NAPROP_METHOD   6
#define PROP_RK2        0
#define PROP_RK4        1
#define PROP_RK5        2
#define PROP_RK6        3
#define PROP_RK7        4
#define PROP_RK8        5
#define PROP_SY2        6
#define PROP_SY4        7
#define PROP_SY6        8
#define PROP_SY8        9

struct CFG_PHYSICSPRM {
	bool   bDistributedMass;	// vessels can define 2-point mass distribution
	bool   bNonsphericalGrav;	// take into account nonspherical planet shapes for gravity calculations
	bool   bRadiationPressure;	// take into account radiation pressure effects
	bool   bAtmWind;            // nonzero wind speeds
	bool   bBaseCollision;      // surface base collision
	bool   bVesselCollision;    // vessel-to-vessel collision
	bool   bOrbitStabilise;		// use Encke orbit stabilisation at high time accelerations
	double Stabilise_PLimit;	// perturbation limit for stabilisation
	double Stabilise_SLimit;	// step size limit for stabilisation
	double PPropSubLimit;		// orbit step target for perturbation subsampling
	int    PPropSubMax;			// max number of subsampling steps (perturbation integration)
	double PPropStepLimit;		// orbit step limit for nonspherical gravity suppression
	int    nLPropLevel;			// number of linear state propagation levels defined
	int    PropMode[MAX_PROP_LEVEL];	// propagation mode indices
	double PropTTgt[MAX_PROP_LEVEL];    // time step targets for the propagation levels
	double PropATgt[MAX_PROP_LEVEL];    // angle step targets for the propagation levels
	double PropTLim[MAX_PROP_LEVEL];	// time step limits for the propagation levels
	double PropALim[MAX_PROP_LEVEL];  // angle step limits for the propagation levels
	double APropSubLimit;		// angle step limit for subsampling
	int    PropSubMax;			// max number of subsampling steps
	double APropCouplingLimit;	// angle step limit for cross term suppresion
	double APropTorqueLimit;	// angle step limit for torque suppression
};

#endif
