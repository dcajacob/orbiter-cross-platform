// Copyright (c) Martin Schweiger
// Licensed under the MIT License

#ifndef __UTIL_H
#define __UTIL_H

#include <windows.h>
#include "Vecmat.h"
#include "OrbiterAPI.h"
#include "Orbiter.h"

extern Orbiter *g_pOrbiter;

#include "Production/SurfaceTypes.h"
// converts a file name into an identifier. Note that this is not guaranteed to be unique.

// should go into the graphics client
inline DWORD GetSurfColour (DWORD r, DWORD g, DWORD b)
{
	DWORD bpp = g_pOrbiter->ViewBPP();
	if (bpp >= 24) return (r << 16) + (g << 8) + b;
	else           return (((r*319)/2559) << 11) + (((g*639)/2559) << 5) + ((b*319)/2559);
}

DWORDLONG Str2Crc (const char *str);
// converts str into an integer identifier (not guaranteed unique!)

// create the directories 
bool MakePath (const char *fname);

// case-insensitive comparison of std::strings
bool iequal(const std::string& s1, const std::string& s2);

#include "Production/GeometryConversions.h"

#include "Production/Random.h"
// uniformly distributed random number, range [0,1]

RECT GetClientPos (HWND hWnd, HWND hChild);
void SetClientPos (HWND hWnd, HWND hChild, RECT &r);

// Floating point output stream formatter
struct FltFormatter
{
	int precision;
	double value;
	FltFormatter (int precision, double value);
	friend std::ostream& operator<< (std::ostream& os, const FltFormatter& v);
};

struct FltFormat
{
	int precision;
	FltFormat (int precision = 6);
	FltFormatter operator() (double value) const;
};

// Convert a CSS color string to a DWORD (in 0xbbggrr format)
DWORD GetCSSColor(const char *col);

#endif //!__UTIL_H