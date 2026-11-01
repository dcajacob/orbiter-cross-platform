// Copyright (c) Martin Schweiger
// Licensed under the MIT License
#ifndef ORBITER_WIND_DATA_H
#define ORBITER_WIND_DATA_H
#include "Vecmat.h"
struct WindPrm {           // per-vessel wind parameters
	double pert_t;            // time for wind perturbation vector
	Vector pert_v;            // wind perturbation vector
};
#endif
