// Licensed under the MIT License
#ifndef ORBITER_PRODUCTION_COCKPIT_SERVICES_H
#define ORBITER_PRODUCTION_COCKPIT_SERVICES_H
#include "CameraServices.h"
#include "CockpitGraphics.h"
#include "BodyServices.h"
#include "RigidBodyServices.h"
#ifdef _WIN32
#include "Orbiter.h"
extern Orbiter* g_pOrbiter;
#else
#include "NativeGraphics.h"
#endif
namespace orbiter::production {
inline oapi::UInt32 CockpitColor(std::uint8_t r,std::uint8_t g,std::uint8_t b) {
#ifdef _WIN32
    return RGB(r,g,b);
#else
    return oapi::UInt32(r)|(oapi::UInt32(g)<<8)|(oapi::UInt32(b)<<16);
#endif
}
inline Config* CockpitConfiguration() {return &GetCameraServices().Configuration();}
inline oapi::CockpitClient* CockpitGraphicsClient() {
#ifdef _WIN32
    return g_pOrbiter->GetGraphicsClient();
#else
    return GetNativeRenderContext().graphics;
#endif
}
inline std::filesystem::path CockpitConfigPath(const char* name) {
#ifdef _WIN32
    return g_pOrbiter->ConfigPath(name);
#else
    return GetBodyServices().ConfigPath(name);
#endif
}
inline bool CockpitReleaseSurface(SURFHANDLE surface) {
#ifdef _WIN32
    return g_pOrbiter->ReleaseSurface(surface);
#else
    auto* graphics=CockpitGraphicsClient();return graphics?graphics->ReleaseTextureResource(surface):false;
#endif
}
inline oapi::UInt32 CockpitDeviceColour(std::uint8_t r,std::uint8_t g,std::uint8_t b) {
#ifdef _WIN32
    return g_pOrbiter->GetDeviceColour(r,g,b);
#else
    auto* graphics=CockpitGraphicsClient();return graphics?graphics->clbkGetDeviceColour(r,g,b):0;
#endif
}
inline bool CockpitFillSurface(SURFHANDLE surface,oapi::UInt32 color) {
#ifdef _WIN32
    return g_pOrbiter->FillSurface(surface,color);
#else
    auto* graphics=CockpitGraphicsClient();return graphics?graphics->clbkFillSurface(surface,color):false;
#endif
}
inline bool CockpitBlt(SURFHANDLE target,oapi::UInt32 x,oapi::UInt32 y,SURFHANDLE source,oapi::UInt32 flags=0) {
#ifdef _WIN32
    return g_pOrbiter->Blt(target,x,y,source,flags);
#else
    auto* graphics=CockpitGraphicsClient();return graphics?graphics->clbkBlt(target,x,y,source,flags):false;
#endif
}
inline bool CockpitBlt(SURFHANDLE target,oapi::UInt32 x,oapi::UInt32 y,SURFHANDLE source,
    oapi::UInt32 sx,oapi::UInt32 sy,oapi::UInt32 width,oapi::UInt32 height,oapi::UInt32 flags=0) {
#ifdef _WIN32
    return g_pOrbiter->Blt(target,x,y,source,sx,sy,width,height,flags);
#else
    auto* graphics=CockpitGraphicsClient();return graphics?graphics->clbkBlt(target,x,y,source,sx,sy,width,height,flags):false;
#endif
}
}
#endif
