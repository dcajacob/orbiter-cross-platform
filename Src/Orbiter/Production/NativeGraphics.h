// Licensed under the MIT License
#ifndef ORBITER_PRODUCTION_NATIVE_GRAPHICS_H
#define ORBITER_PRODUCTION_NATIVE_GRAPHICS_H
#include "Export.h"
#include "NativeRenderApi.h"
#include "ResourceResolver.h"
#include "SceneLabels.h"
#include "FlightInput.h"
#include <vector>
class Config;class Camera;class PlanetarySystem;class MeshManager;class TimeData;class Vessel;class Pane;class Select;class InputBox;
namespace oapi {class ParticleStream;}
namespace orbiter::production {
// Internal same-build native renderer contract. No window handles, GPU classes
// or renderer math enter production numerical objects or the Windows SDK.
enum class RenderMouseAction {Move,LeftDown,LeftUp,RightDown,RightUp,Wheel};
struct RenderMouseEvent {RenderMouseAction action;int x=0,y=0;double wheel=0;};
struct RenderInput {FlightInput flight;std::vector<RenderMouseEvent> mouse;bool close=false;int width=0,height=0;double yaw=0,pitch=0,zoom=0;};
struct NativeJoystickDevice {unsigned index;std::string name;int axes;};
class ORBITER_PRODUCTION_API NativeGraphics {
public:
    virtual ~NativeGraphics()=default;
    using LABELSPEC=SceneLabel;using LABELLIST=SceneLabelList;using LABELTYPE=SceneLabelType;
    struct ConstLabelRec {std::string fullLabel,abbrLabel;float lngCnt,latCnt;};
    virtual const void* GetConfigParam(oapi::UInt32) const=0;
    virtual const std::vector<LABELLIST>& GetCelestialMarkers() const=0;
    virtual void clbkGetViewportSize(oapi::UInt32*,oapi::UInt32*) const=0;
    oapi::Font* clbkCreateFont(int height,bool prop,const char* face,FontStyle style=FONT_NORMAL,int orientation=0) {return CreateFontResource(height,prop,face,style,orientation);}
    oapi::Pen* clbkCreatePen(int style,int width,oapi::UInt32 color) {return CreatePenResource(style,width,color);}
    void clbkReleaseFont(oapi::Font* font) {ReleaseFontResource(font);}
    void clbkReleasePen(oapi::Pen* pen) {ReleasePenResource(pen);}
    oapi::Brush* clbkCreateBrush(oapi::UInt32 color) {return CreateBrushResource(color);}
    void clbkReleaseBrush(oapi::Brush* brush) {ReleaseBrushResource(brush);}
    oapi::Sketchpad* clbkGetSketchpad(SURFHANDLE surface) {return AcquireSketchpad(surface);}

    void clbkReleaseSketchpad(oapi::Sketchpad* pad) {ReleaseSketchpadResource(pad);}
    virtual SURFHANDLE clbkCreateSurfaceEx(oapi::UInt32,oapi::UInt32,oapi::UInt32)=0;
    virtual oapi::UInt32 clbkGetDeviceColour(std::uint8_t,std::uint8_t,std::uint8_t)=0;
    virtual bool clbkFillSurface(SURFHANDLE,oapi::UInt32) const=0;
    virtual bool clbkBlt(SURFHANDLE,oapi::UInt32,oapi::UInt32,SURFHANDLE,oapi::UInt32=0) const=0;
    virtual bool clbkBlt(SURFHANDLE,oapi::UInt32,oapi::UInt32,SURFHANDLE,oapi::UInt32,oapi::UInt32,oapi::UInt32,oapi::UInt32,oapi::UInt32=0) const=0;
    virtual bool clbkGetRenderParam(oapi::UInt32,oapi::UInt32*) const=0;
    virtual SURFHANDLE clbkLoadSurface(const char*,oapi::UInt32,bool=false)=0;
    virtual SURFHANDLE clbkCreateTexture(oapi::UInt32,oapi::UInt32)=0;
    virtual bool clbkGetSurfaceSize(SURFHANDLE,oapi::UInt32*,oapi::UInt32*)=0;
    virtual void clbkIncrSurfaceRef(SURFHANDLE)=0;
    virtual bool clbkReleaseSurface(SURFHANDLE)=0;
    virtual bool clbkScaleBlt(SURFHANDLE,oapi::UInt32,oapi::UInt32,oapi::UInt32,oapi::UInt32,SURFHANDLE,oapi::UInt32,oapi::UInt32,oapi::UInt32,oapi::UInt32,oapi::UInt32=0) const=0;
    virtual void clbkRender2DPanel(SURFHANDLE*,MESHHANDLE,MATRIX3*,bool=false)=0;
    virtual void clbkRender2DPanel(SURFHANDLE*,MESHHANDLE,MATRIX3*,float,bool=false)=0;
    SURFHANDLE clbkLoadTexture(const char* name,oapi::UInt32 flags) {return LoadTextureResource(name,flags);}
    virtual int DesktopHeight() const=0;
    virtual std::vector<NativeJoystickDevice> Joysticks() const=0;
    virtual oapi::SdkPoint CursorPosition() const=0;
    virtual void Open()=0;
    virtual RenderInput Poll()=0;
    virtual void Resize(int,int)=0;
    virtual void Status(const std::string&)=0;
    virtual void PostCreation()=0;
    virtual void NewVessel(OBJHANDLE)=0;
    virtual void DeleteVessel(OBJHANDLE)=0;
    virtual void ReplayGuiInput(const std::string&,int,int,const std::string&)=0;
    virtual void InitGui()=0;
    virtual void NewGuiFrame()=0;
    virtual void RenderGui()=0;
    virtual void ShutdownGui()=0;
    virtual void Render()=0;
    virtual bool Present()=0;
    virtual void CloseSession()=0;
    virtual void Close()=0;
    virtual SURFHANDLE LoadTextureResource(const char*,oapi::UInt32)=0;
    virtual std::uint64_t GuiTextureId(SURFHANDLE)=0;
    virtual bool ReleaseTextureResource(SURFHANDLE)=0;
    virtual void StoreMesh(MESHHANDLE,const char*)=0;
    virtual void VisualEvent(OBJHANDLE,VISHANDLE,oapi::UInt32,std::uintptr_t)=0;
    virtual oapi::Font* CreateFontResource(int,bool,const char*,FontStyle,int)=0;
    virtual void ReleaseFontResource(oapi::Font*)=0;
    virtual oapi::Pen* CreatePenResource(int,int,oapi::UInt32)=0;
    virtual void ReleasePenResource(oapi::Pen*)=0;
    virtual oapi::Brush* CreateBrushResource(oapi::UInt32)=0;
    virtual void ReleaseBrushResource(oapi::Brush*)=0;
    virtual oapi::Sketchpad* AcquireSketchpad(SURFHANDLE)=0;
    virtual void ReleaseSketchpadResource(oapi::Sketchpad*)=0;
    virtual SURFHANDLE CreateSurfaceResource(int,int)=0;
    virtual int MeshGroup(DEVMESHHANDLE,oapi::UInt32,GROUPREQUESTSPEC*)=0;
    virtual MESHHANDLE clbkGetMesh(VISHANDLE,oapi::UInt)=0;
    virtual int EditMeshGroup(DEVMESHHANDLE,int,GROUPEDITSPEC*)=0;
    virtual bool SetMeshTexture(DEVMESHHANDLE,int,SURFHANDLE)=0;
    virtual bool clbkSaveSurfaceToImage(SURFHANDLE,const char*,oapi::ImageFileFormat,float)=0;
    virtual bool SetMeshProperty(DEVMESHHANDLE,int,int)=0;
    // The original GraphicsClient reports unsupported extended material properties as 2.
    virtual int clbkSetMeshMaterialEx(DEVMESHHANDLE,oapi::UInt32,MatProp,const oapi::FVECTOR4*) { return 2; }
    virtual int SetMeshMaterial(DEVMESHHANDLE,int,const MATERIAL*)=0;
    virtual oapi::ParticleStream* Exhaust(PARTICLESTREAMSPEC*,OBJHANDLE,const double*,const VECTOR3*,const VECTOR3*)=0;
    virtual oapi::ParticleStream* Exhaust(PARTICLESTREAMSPEC*,OBJHANDLE,const double*,const VECTOR3&,const VECTOR3&)=0;
    virtual oapi::ParticleStream* Reentry(PARTICLESTREAMSPEC*,OBJHANDLE)=0;
};
struct NativeRenderContext {
    Config* configuration=nullptr;PlanetarySystem* world=nullptr;Camera* camera=nullptr;
    Vessel* focus=nullptr;TimeData* time=nullptr;MeshManager* meshes=nullptr;
    class VesselLifetimeServices* lifetime=nullptr;
    const ResourceResolver *textures=nullptr,*highTextures=nullptr,*planetTextures=nullptr,*meshFiles=nullptr,*programFiles=nullptr;
    const ResourceResolver* configurationFiles=nullptr;
    class NativeAnnotations* annotations=nullptr;
    class ScriptApplication* scriptApplication=nullptr;
    std::filesystem::path scriptSaveDirectory;
    class NativeScriptHost* scripts=nullptr;
    NativeGraphics* graphics=nullptr;Pane* cockpitPane=nullptr;Select* cockpitSelect=nullptr;InputBox* cockpitInput=nullptr;HELPCONTEXT* cockpitHelp=nullptr;
    bool paused=true,showGrapple=false;
    bool optionsUsed=false;
    int joystickThrottleAxis=-1,joystickTwistAxis=2;
    std::filesystem::path evidence;double captureTime=0;
};
ORBITER_PRODUCTION_API NativeRenderContext* BindNativeRenderContext(NativeRenderContext*);
ORBITER_PRODUCTION_API Pane* ActiveCockpitPane();
ORBITER_PRODUCTION_API NativeRenderContext& GetNativeRenderContext();
ORBITER_PRODUCTION_API SURFHANDLE RenderCockpitMfd(int);
ORBITER_PRODUCTION_API SURFHANDLE RenderCockpitVcMfd(int,const VCMFDSPEC**);
ORBITER_PRODUCTION_API SURFHANDLE RenderCockpitVcHud(const VCHUDSPEC**);
ORBITER_PRODUCTION_API void RenderCockpitOverlay();
ORBITER_PRODUCTION_API const void* RenderConfig(oapi::UInt32);
ORBITER_PRODUCTION_API bool RenderTexturePath(const char*,char*,bool planet);
ORBITER_PRODUCTION_API void RenderRegisterVisual(OBJHANDLE,VISHANDLE);
ORBITER_PRODUCTION_API void RenderUnregisterVisual(OBJHANDLE);
ORBITER_PRODUCTION_API oapi::UInt32 RenderBaseTiles(OBJHANDLE,const SurftileSpec**);
ORBITER_PRODUCTION_API void RenderBaseStructures(OBJHANDLE,MESHHANDLE**,oapi::UInt32*,MESHHANDLE**,oapi::UInt32*);
ORBITER_PRODUCTION_API void RenderBaseShadows(OBJHANDLE,MESHHANDLE**,double**,oapi::UInt32*);
ORBITER_PRODUCTION_API bool RenderElevationGrid(ELEVHANDLE,int,int,int,int,int,int,std::int16_t*,float*,double*);
ORBITER_PRODUCTION_API bool RenderElevationGrid(ELEVHANDLE,int,int,int,int,int,int,std::int16_t*,std::int16_t*,double*);
ORBITER_PRODUCTION_API const std::vector<SceneLabelList>& RenderCelestialMarkers();
ORBITER_PRODUCTION_API oapi::UInt32 RenderSurfaceMarkers(OBJHANDLE,const SceneLabelList**);
ORBITER_PRODUCTION_API oapi::UInt32 RenderSurfaceLegend(OBJHANDLE,const SceneLabelType**);
ORBITER_PRODUCTION_API void RenderDetachParticle(OBJHANDLE,oapi::ParticleStream*);
ORBITER_PRODUCTION_API bool RenderHasCelestialModule(OBJHANDLE);
ORBITER_PRODUCTION_API OBJHANDLE RenderCelestialParent(OBJHANDLE);
}
#endif
