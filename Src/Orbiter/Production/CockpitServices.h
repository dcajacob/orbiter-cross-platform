// Licensed under the MIT License
#ifndef ORBITER_PRODUCTION_COCKPIT_SERVICES_H
#define ORBITER_PRODUCTION_COCKPIT_SERVICES_H
#include "CameraServices.h"
#include "CockpitGraphics.h"
#include "BodyServices.h"
#include "RigidBodyServices.h"
class Pane;class Select;class InputBox;
#ifdef _WIN32
#include "Orbiter.h"
extern Orbiter* g_pOrbiter;
extern Pane* g_pane;extern Select* g_select;extern InputBox* g_input;extern HELPCONTEXT DefHelpContext;
extern TimeData td;extern PlanetarySystem* g_psys;extern Vessel* g_focusobj;
extern Camera* g_camera;
#else
#include "NativeGraphics.h"
#include <stdexcept>
#endif
namespace orbiter::production {
inline Camera* CockpitCamera() {
#ifdef _WIN32
    return g_camera;
#else
    auto* camera=GetNativeRenderContext().camera;
    if(!camera)throw std::logic_error("Native cockpit camera is not bound");return camera;
#endif
}
#ifndef _WIN32
inline oapi::SdkPoint CockpitCursor() {
    auto* graphics=GetNativeRenderContext().graphics;
    if(!graphics)throw std::logic_error("Native cockpit cursor is not bound");return graphics->CursorPosition();
}
#endif
namespace CockpitMouse {
#ifdef _WIN32
constexpr oapi::UInt LeftDown=WM_LBUTTONDOWN,RightDown=WM_RBUTTONDOWN,LeftUp=WM_LBUTTONUP,RightUp=WM_RBUTTONUP,Wheel=WM_MOUSEWHEEL;
#else
constexpr oapi::UInt LeftDown=1,RightDown=2,LeftUp=3,RightUp=4,Wheel=5;
#endif
}
inline oapi::SdkRectangle CockpitRectangle(int left,int top,int right,int bottom) {
#ifdef _WIN32
    return _R(left,top,right,bottom);
#else
    return {left,top,right,bottom};
#endif
}
inline int CockpitScreenHeight() {
#ifdef _WIN32
    return GetSystemMetrics(SM_CYSCREEN);
#else
    auto* graphics=GetNativeRenderContext().graphics;
    if(!graphics)throw std::logic_error("Native display service is not bound");return graphics->DesktopHeight();
#endif
}
inline TimeData& CockpitTime() {
#ifdef _WIN32
    return td;
#else
    return GetRigidBodyServices().Time();
#endif
}
inline PlanetarySystem* CockpitWorld() {
#ifdef _WIN32
    return g_psys;
#else
    return GetRigidBodyServices().World();
#endif
}
inline Vessel* CockpitFocus() {
#ifdef _WIN32
    return g_focusobj;
#else
    return GetCameraServices().Focus();
#endif
}
inline Pane* CockpitPane() {
#ifdef _WIN32
    return g_pane;
#else
    auto* pane=GetNativeRenderContext().cockpitPane;
    if(!pane)throw std::logic_error("Native cockpit pane is not bound");return pane;
#endif
}
inline Select* CockpitSelect() {
#ifdef _WIN32
    return g_select;
#else
    auto* select=GetNativeRenderContext().cockpitSelect;
    if(!select)throw std::logic_error("Native cockpit selection dialog is not bound");return select;
#endif
}
inline InputBox* CockpitInput() {
#ifdef _WIN32
    return g_input;
#else
    auto* input=GetNativeRenderContext().cockpitInput;
    if(!input)throw std::logic_error("Native cockpit input dialog is not bound");return input;
#endif
}
inline HELPCONTEXT& CockpitHelpContext() {
#ifdef _WIN32
    return DefHelpContext;
#else
    auto* help=GetNativeRenderContext().cockpitHelp;
    if(!help)throw std::logic_error("Native cockpit help context is not bound");return *help;
#endif
}
inline std::uint16_t CockpitHighWord(oapi::UInt32 value) {
#ifdef _WIN32
    return HIWORD(value);
#else
    return std::uint16_t(value>>16);
#endif
}
inline std::uint16_t CockpitLowWord(oapi::UInt32 value) {
#ifdef _WIN32
    return LOWORD(value);
#else
    return std::uint16_t(value&0xffff);
#endif
}
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
    // Original optional palette/coast/contour readers test their file stream.
    // Required world/module configuration continues through BodyServices.
    const auto* files=GetNativeRenderContext().configurationFiles;
    if(!files)throw std::logic_error("Native cockpit configuration resolver is not bound");
    std::string path=name;if(std::filesystem::path(path).extension().empty())path+=".cfg";
    return files->Contains(path)?files->Resolve(path):files->Root()/ResourceResolver::Normalize(path);
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
