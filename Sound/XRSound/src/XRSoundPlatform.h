// Licensed under the MIT License
#pragma once

#ifdef _WIN32
#include <Windows.h>
#include "Orbitersdk.h"
#else
#include "NativeVesselAPI.h"
#include "Production/NativeRenderApi.h"
#include "Production/ResourceResolver.h"
#include <algorithm>
#include <cassert>
#include <random>
#include <stdexcept>
#include <string>
#include <strings.h>

#define _ASSERTE assert

inline int _stricmp(const char* a, const char* b) { return strcasecmp(a, b); }
inline int _strnicmp(const char* a, const char* b, std::size_t n) { return strncasecmp(a, b, n); }

// An old handle may have been deleted between sound updates. Only compare it
// with live handles before asking the vessel SDK to dereference it.
inline bool oapiIsVessel(OBJHANDLE handle)
{
    for (oapi::UInt32 i = 0; i < oapiGetVesselCount(); ++i)
        if (oapiGetVesselByIndex(i) == handle)
            return true;
    return false;
}
#endif

inline double XRSoundRandom()
{
#ifdef _WIN32
    return oapiRand();
#else
    // Audio scheduling must not consume the native simulation's random stream.
    static std::mt19937 generator(std::random_device{}());
    return std::generate_canonical<double, 53>(generator);
#endif
}

namespace xrsound {
#ifndef _WIN32
extern const orbiter::production::ResourceResolver* resources;
#endif

inline std::string AssetPath(const char* name, bool directory = false)
{
#ifdef _WIN32
    (void)directory;
    return name;
#else
    if (name && *name && resources) {
        try {
            if (directory && resources->ContainsDirectory(name))
                return resources->ResolveDirectory(name).string();
            if (!directory && resources->Contains(name))
                return resources->Resolve(name).string();
        } catch (const std::invalid_argument&) {
            // Stock configs contain relative paths. Missing or invalid assets
            // use the same failure path as a file that cannot be opened.
        }
    }
    return {};
#endif
}
}
