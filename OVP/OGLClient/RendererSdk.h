// Licensed under the MIT License
#pragma once
#ifdef _WIN32
#include "GraphicsAPI.h"
using RendererHost=oapi::GraphicsClient;
using RendererModuleContext=HINSTANCE;
#define ORBITER_RENDER_OVERRIDE override
#else
#include "Native/NativeRenderHost.h"
using RendererHost=NativeRenderHost;
using RendererModuleContext=void*;
#define ORBITER_RENDER_OVERRIDE
#endif

#ifdef _WIN32
inline bool RendererHasCelestialModule(OBJHANDLE object) {return oapiGetCelbodyInterface(object)!=nullptr;}
inline OBJHANDLE RendererCelestialParent(OBJHANDLE object) {auto* cb=oapiGetCelbodyInterface(object);return cb && cb->Version()>=2?static_cast<CELBODY2*>(cb)->GetParent():nullptr;}
#else
inline bool RendererHasCelestialModule(OBJHANDLE object) {return RenderHasCelestialModule(object);}
inline OBJHANDLE RendererCelestialParent(OBJHANDLE object) {return RenderCelestialParent(object);}
#endif
