// Licensed under the MIT License
#pragma once
#include "Production/NativeGraphics.h"
#include <stdexcept>
using namespace orbiter::production;
class NativeRenderHost:public NativeGraphics {
public:
    explicit NativeRenderHost(void*) {}
    virtual bool clbkInitialise() {return true;}
    // Session resource ownership is in OGLClient; the base owns no resources.
    void clbkCloseSession(bool) {}
    const void* GetConfigParam(oapi::UInt32 id) const {return RenderConfig(id);}
    bool TexturePath(const char* name,char* path) const {return RenderTexturePath(name,path,false);}
    bool PlanetTexturePath(const char* name,char* path) const {return RenderTexturePath(name,path,true);}
    void RegisterVisObject(OBJHANDLE body,VISHANDLE visual) {RenderRegisterVisual(body,visual);}
    void UnregisterVisObject(OBJHANDLE body) {RenderUnregisterVisual(body);}
    using LABELSPEC=SceneLabel;using LABELLIST=SceneLabelList;using LABELTYPE=SceneLabelType;
    const std::vector<LABELLIST>& GetCelestialMarkers() const {return RenderCelestialMarkers();}
    oapi::UInt32 GetSurfaceMarkers(OBJHANDLE body,const LABELLIST** lists) const {return RenderSurfaceMarkers(body,lists);}
    oapi::UInt32 GetSurfaceMarkerLegend(OBJHANDLE body,const LABELTYPE** types) const {return RenderSurfaceLegend(body,types);}
    oapi::UInt32 GetBaseTileList(OBJHANDLE base,const SurftileSpec** tiles) const {return RenderBaseTiles(base,tiles);}
    void GetBaseStructures(OBJHANDLE base,MESHHANDLE** a,oapi::UInt32* na,MESHHANDLE** b,oapi::UInt32* nb) const {RenderBaseStructures(base,a,na,b,nb);}
    void GetBaseShadowGeometry(OBJHANDLE base,MESHHANDLE** m,double** e,oapi::UInt32* n) const {RenderBaseShadows(base,m,e,n);}
    bool ElevationGrid(ELEVHANDLE e,int a,int b,int c,int d,int f,int g,std::int16_t* h,float* i,double* j=nullptr) const {return RenderElevationGrid(e,a,b,c,d,f,g,h,i,j);}
    bool ElevationGrid(ELEVHANDLE e,int a,int b,int c,int d,int f,int g,std::int16_t* h,std::int16_t* i,double* j=nullptr) const {return RenderElevationGrid(e,a,b,c,d,f,g,h,i,j);}
    SURFHANDLE GetVCHUDSurface(const VCHUDSPEC**) const {throw std::runtime_error("Native external view has no cockpit HUD surface");}
    SURFHANDLE GetVCMFDSurface(int,const VCMFDSPEC**) const {throw std::runtime_error("Native external view has no virtual cockpit MFD");}
    SURFHANDLE GetMFDSurface(int) const {throw std::runtime_error("Native external view has no cockpit MFD");}
    void Render2DOverlay() {throw std::runtime_error("Native external view has no cockpit overlay");}
    bool UseStencilBuffer() const {return true;}
};
#include "Production/NativeParticle.h"
