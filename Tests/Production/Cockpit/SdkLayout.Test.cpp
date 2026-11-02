// Licensed under the MIT License
// SDK records used across the real engine/client/vessel module boundary.
#ifdef _WIN32
#include "Orbitersdk.h"
#else
#include "NativeVesselAPI.h"
#endif
#include <cstddef>
#include <cstdint>
#include <iostream>
#include <type_traits>

static_assert(sizeof(MFDSPEC)==32 && offsetof(MFDSPEC,bt_yofs)==24);
static_assert(sizeof(VCMFDSPEC)==8 && sizeof(EXTMFDSPEC)==44);
static_assert(sizeof(VCHUDSPEC)==40 && offsetof(VCHUDSPEC,size)==32);
static_assert(sizeof(HUDPAINTSPEC)==32 && offsetof(HUDPAINTSPEC,Scale)==16);
static_assert(alignof(MFDBUTTONMENU)==1);
static_assert(MAXMFD==12 && BUILTIN_MFD_MODES==10 && MFD_COMMS==10 && HUD_DOCKING==3);
static_assert(std::is_same_v<decltype(MFDMODESPEC{}.key),oapi::UInt32>);
static_assert(std::is_abstract_v<ImGuiDialog> && std::has_virtual_destructor_v<ImGuiDialog>);
static_assert(sizeof(HELPCONTEXT)==4*sizeof(char*));
#if INTPTR_MAX==INT64_MAX
static_assert(sizeof(MFDMODESPEC)==24 && offsetof(MFDMODESPEC,msgproc)==16);
static_assert(sizeof(MFDMODESPECEX)==32 && offsetof(MFDMODESPECEX,context)==16);
static_assert(sizeof(MFDBUTTONMENU)==17 && sizeof(HUDPARAM)==8);
#endif
#ifdef _WIN32
using OriginalMfdCallback=OAPI_MSGTYPE(*)(UINT,UINT,WPARAM,LPARAM);
static_assert(std::is_same_v<decltype(MFDMODESPEC{}.msgproc),OriginalMfdCallback>);
static_assert(std::is_same_v<decltype(MFDSPEC{}.pos),RECT>);
static_assert(std::is_same_v<decltype(VCMFDSPEC{}.nmesh),DWORD>);
#else
using NativeMfdCallback=std::intptr_t(*)(oapi::UInt,oapi::UInt,std::uintptr_t,std::intptr_t);
static_assert(std::is_same_v<decltype(MFDMODESPEC{}.msgproc),NativeMfdCallback>);
static_assert(std::is_same_v<decltype(MFDSPEC{}.pos),oapi::SdkRectangle>);
#endif
static_assert(PANEL_MOUSE_LBDOWN==1 && PANEL_MOUSE_RBDOWN==2 && PANEL_MOUSE_LBUP==4 && PANEL_MOUSE_RBUP==8);
static_assert(PANEL_MOUSE_LBPRESSED==16 && PANEL_MOUSE_RBPRESSED==32 && PANEL_MOUSE_ONREPLAY==64);
int main(){std::cout<<"Cockpit SDK field layouts, packed menu records and callback types passed\n";}
