// Copyright (c) Martin Schweiger
// Licensed under the MIT License
#include "Vecmat.h"
#include <cmath>
#ifdef _WIN32
#define ORBITER_FLIGHT_EXPORT __declspec(dllexport)
#else
#define ORBITER_FLIGHT_EXPORT __attribute__((visibility("default")))
#endif

ORBITER_FLIGHT_EXPORT double oapiGetInducedDrag (double cl, double A, double eps)
{
	return (cl*cl)/(Pi*A*eps);
}

ORBITER_FLIGHT_EXPORT double oapiGetWaveDrag (double M, double M1, double M2, double M3, double cmax)
{
	if (M < M1) return 0.0;
	if (M < M2) return cmax * (M-M1)/(M2-M1);
	if (M < M3) return cmax;
	return cmax * sqrt ((M3*M3-1.0)/(M*M-1.0));
}
