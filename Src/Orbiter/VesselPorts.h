// Copyright (c) Martin Schweiger
// Licensed under the MIT License
#ifndef ORBITER_VESSEL_PORTS_H
#define ORBITER_VESSEL_PORTS_H
#include "Vecmat.h"
#include "Production/CoreTypes.h"
class Vessel;
class Nav_IDS;
typedef struct PortSpec {      // docking port definition
	Vector ref;             // docking port reference pos
	Vector dir;             // approach direction
	Vector rot;             // longitudinal rotation alignment direction
	Vessel *mate;           // vessel attached to port (NULL for none)
	Vessel *pending;        // vessel being currently docked/undocked
	Vessel *owner;			// vessel that's owns this docking port
	int status;             // 0=normal (docked/free), 1=docking in progress, 2=undocking in progress
	orbiter::production::UInt32 matedock;         // mate dock index
	Nav_IDS *ids;           // instrument docking system specs (NULL if not available)
	bool autodock;			// Use auto capture on docking
} PortSpec;
#endif
