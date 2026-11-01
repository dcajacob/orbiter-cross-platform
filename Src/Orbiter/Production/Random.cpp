// Copyright (c) Martin Schweiger
// Licensed under the MIT License
#include "Random.h"
#include <cstdlib>

double rand1()
{
	static double irmax = 1.0/(double)RAND_MAX;
	return (double)rand()*irmax;
}
