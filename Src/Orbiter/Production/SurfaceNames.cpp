// Copyright (c) Martin Schweiger
// Licensed under the MIT License
#include "SurfaceTypes.h"
#include <cctype>
orbiter::production::SurfaceName NameToId (const char *name)
{
	orbiter::production::SurfaceName id = 0;
	const char *c;
	char *cid = (char*)&id;
	int i = 0;
	for (c = name; *c; c++, i++) cid[i%8] += toupper (*c);
	return id;
}
