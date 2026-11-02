// Copyright (c) Martin Schweiger
// Licensed under the MIT License
// Production SDK read/delegation functions, adapted to the actual native world.
#include "NativeGraphics.h"
#include "VesselLifetime.h"
#include "VesselServices.h"
#include "RigidBodyServices.h"
#include "CelestialServices.h"
#include "GeometryConversions.h"
#include "Body.h"
#include "Vessel.h"
#include "Planet.h"
#include "Base.h"
#include "Camera.h"
#include "Config.h"
#include "PsysCore.h"
#include "Mesh.h"
#include "elevmgr.h"
#include <cstring>
#include <iostream>
#include <stdexcept>
using namespace orbiter::production;
using std::ifstream;
namespace {
Vessel* liveVessel(OBJHANDLE handle) {
    for(auto* vessel:GetNativeRenderContext().world->GetVessels())if(vessel==handle)return vessel;
    return nullptr;
}
Body* liveBody(OBJHANDLE handle) {
    auto* world=GetNativeRenderContext().world;
    for(int i=0;i<world->nObj();++i)if(world->GetObj(i)==handle)return world->GetObj(i);
    return nullptr;
}
VesselLifetimeServices& lifetime() {
    auto* result=GetNativeRenderContext().lifetime;
    if(!result)throw std::logic_error("Native vessel lifetime service is not bound");return *result;
}
void validateCreation(const char* name,const char* classname) {
    if(!name || !*name || std::strlen(name)>=64 || !classname || !*classname || std::strpbrk(name,"\r\n:;, /\\") ||
       GetNativeRenderContext().world->GetVessel(name,true))throw std::runtime_error("Invalid or duplicate native vessel name/class");
}
}
OBJHANDLE oapiSetFocusObject(OBJHANDLE handle) {
    auto* vessel=liveVessel(handle);if(!vessel)return nullptr;
    return orbiter::production::SetFocusObject(lifetime(),vessel);
}
VESSEL* oapiGetFocusInterface() {auto* vessel=GetNativeRenderContext().focus;return vessel?vessel->GetModuleInterface():nullptr;}
OBJHANDLE oapiGetVesselByName(char* name) {return GetNativeRenderContext().world->GetVessel(name,true);}
OBJHANDLE oapiGetVesselByIndex(int index) {auto* world=GetNativeRenderContext().world;return index>=0 && index<world->nVessel()?world->GetVessel(index):nullptr;}
oapi::UInt32 oapiGetVesselCount() {return GetNativeRenderContext().world->nVessel();}
OBJHANDLE oapiCreateVessel(const char* name,const char* classname,const VESSELSTATUS& status) {
    validateCreation(name,classname);
    auto* vessel=new Vessel(GetNativeRenderContext().world,name,classname,status);
    GetVesselServices().InsertVessel(vessel);return vessel;
}
OBJHANDLE oapiCreateVesselEx(const char* name,const char* classname,const void* status) {
    validateCreation(name,classname);
    if(!status || (*static_cast<const int*>(status)!=1 && *static_cast<const int*>(status)!=2))
        throw std::runtime_error("Unsupported native vessel status version");
    auto* vessel=new Vessel(GetNativeRenderContext().world,name,classname,status);
    GetVesselServices().InsertVessel(vessel);return vessel;
}
bool oapiDeleteVessel(OBJHANDLE handle,OBJHANDLE alternative) {
    auto* vessel=liveVessel(handle);if(!vessel)return false;
    if(GetNativeRenderContext().camera->Target()==vessel && alternative) {
        auto* replacement=liveBody(alternative);if(!replacement || replacement==vessel)return false;
        lifetime().SetView(replacement,1);
    }
    vessel->RequestDestruct();return true;
}
namespace {char debugMessage[1024]{};void RenderLog(const char* text) {std::clog<<text<<'\n';}}
 double oapiCameraAperture ()
{
	return GetNativeRenderContext().camera->Aperture();
}

 void oapiCameraGlobalDir (VECTOR3 *gdir)
{
	const Vector gd = GetNativeRenderContext().camera->Direction();
	gdir->x = gd.x;
	gdir->y = gd.y;
	gdir->z = gd.z;
}

 void oapiCameraGlobalPos (VECTOR3 *gpos)
{
	const Vector *gp = GetNativeRenderContext().camera->GPosPtr();
	gpos->x = gp->x;
	gpos->y = gp->y;
	gpos->z = gp->z;
}

 bool oapiCameraInternal ()
{
	return GetNativeRenderContext().camera->IsInternal();
}

 OBJHANDLE oapiCameraProxyGbody ()
{
	return (OBJHANDLE)GetNativeRenderContext().camera->ProxyPlanet();
}

 void oapiCameraRotationMatrix (MATRIX3 *rmat)
{
	const Matrix &m = GetNativeRenderContext().camera->GRot();
	for (int i = 0; i < 9; i++) rmat->data[i] = m.data[i];

}

 int oapiCockpitMode ()
{
	return 0 /* explicit external view; no cockpit active */;
}

 oapi::Font *oapiCreateFont (int height, bool prop, char *face, FontStyle style)
{
	NativeGraphics *gc = GetNativeRenderContext().graphics;
	oapi::Font *font = NULL;
	if (gc) font = gc->CreateFontResource (height, prop, face, style, 0);
	return font;
}

 oapi::Pen *oapiCreatePen (int style, int width, oapi::UInt32 col)
{
	NativeGraphics *gc = GetNativeRenderContext().graphics;
	if (gc) return gc->CreatePenResource (style, width, col);
	else    return NULL;
}

 SURFHANDLE oapiCreateSurface (int width, int height)
{
	NativeGraphics *gc = GetNativeRenderContext().graphics;
	return (gc ? gc->CreateSurfaceResource (width, height) : NULL);
}

 char *oapiDebugString ()
{
	return debugMessage;
}

 void oapiDeleteMesh (MESHHANDLE hMesh)
{
	Mesh *mesh = (Mesh*)hMesh;
	if (mesh) delete mesh;
}

 ELEVHANDLE oapiElevationManager (OBJHANDLE hPlanet)
{
	Body *body = (Body*)hPlanet;
	if (body->Type() != OBJTP_PLANET) return 0;
	Planet *planet = (Planet*)body;
	return (ELEVHANDLE)planet->ElevMgr();
}

 void oapiEquToLocal (OBJHANDLE hObj, double lng, double lat, double rad, VECTOR3 *loc)
{
	if (((Body*)hObj)->s0) {
		Vector vloc;
		((Body*)hObj)->EquatorialToLocal(lng, lat, rad, vloc);
		loc->x = vloc.x, loc->y = vloc.y, loc->z = vloc.z;
	}
}

 OBJHANDLE oapiGetBaseByIndex (OBJHANDLE hPlanet, int index)
{
	Planet *p = (Planet*)hPlanet;
	if (index < 0 || index >= p->nBase()) return 0;
	return (OBJHANDLE)p->GetBase (index);
}

 oapi::UInt32 oapiGetBaseCount (OBJHANDLE hPlanet)
{
	Body *body = (Body*)hPlanet;
	return (body->Type() == OBJTP_PLANET ? ((Planet*)body)->nBase() : 0);
}

 OBJHANDLE oapiGetBasePlanet (OBJHANDLE hBase)
{
	return (OBJHANDLE)((Base*)hBase)->RefPlanet();
}

 oapi::UInt32 oapiGetColour (oapi::UInt32 red, oapi::UInt32 green, oapi::UInt32 blue)
{
	return ((red << 16) + (green << 8) + blue);
}

 OBJHANDLE oapiGetFocusObject ()
{
	return (OBJHANDLE)GetNativeRenderContext().focus;
}

 OBJHANDLE oapiGetGbodyByIndex (int index)
{
	return (GetNativeRenderContext().world ? GetNativeRenderContext().world->GetGravObj (index) : 0);
}

 oapi::UInt32 oapiGetGbodyCount ()
{
	return (GetNativeRenderContext().world ? GetNativeRenderContext().world->nGrav() : 0);
}

 void oapiGetGlobalPos (OBJHANDLE hObj, VECTOR3 *pos)
{
	if (((Body*)hObj)->s0) {
		Vector gp(((Body*)hObj)->GPos());
		pos->x = gp.x, pos->y = gp.y, pos->z = gp.z;
	}
}

 double oapiGetMass (OBJHANDLE hObj)
{
	return ((Body*)hObj)->Mass();
}

 const char* oapiGetMeshFilename(MESHHANDLE hMesh)
{
	return hMesh ? ((Mesh*)hMesh)->GetName() : NULL;
}

 int oapiGetMeshGroup (DEVMESHHANDLE hMesh, oapi::UInt32 grpidx, GROUPREQUESTSPEC *grs)
{
	NativeGraphics *gc = GetNativeRenderContext().graphics;
	return (gc ? gc->MeshGroup (hMesh, grpidx, grs) : -1);
}

 OBJHANDLE oapiGetObjectByIndex (int index)
{
	return (OBJHANDLE)(GetNativeRenderContext().world ? GetNativeRenderContext().world->GetObj (index) : 0);
}

 oapi::UInt32 oapiGetObjectCount ()
{
	return (GetNativeRenderContext().world ? GetNativeRenderContext().world->nObj() : 0);
}

 void oapiGetObjectName (OBJHANDLE hObj, char *name, int n)
{
	strncpy (name, ((Body*)hObj)->Name(), n);
}

 const void *oapiGetObjectParam (OBJHANDLE hObj, oapi::UInt32 paramtype)
{
	switch (((Body*)hObj)->Type()) {
	case OBJTP_VESSEL:
		return ((Vessel*)hObj)->GetParam (paramtype);
	case OBJTP_PLANET:
		return ((Planet*)hObj)->GetParam (paramtype);
	default:
		return ((Body*)hObj)->GetParam (paramtype);
	}
}

 int oapiGetObjectType (OBJHANDLE hObj)
{
	int i;

	Body *body = (Body*)hObj;

	// Try for celestial body
	CelestialBody *cbody = 0;
	try {
		cbody = dynamic_cast<CelestialBody*>(body);
	}
	catch(...) {
		cbody = 0;
	}
	if (cbody) return body->Type();

	// Try for surface base
	Base *base = 0;
	try {
		base = dynamic_cast<Base*>(body);
	}
	catch(...) {
		base = 0;
	}
	if (base) return body->Type();

	// Try for vessel. Here we go through the list of current
	// vessels, to avoid deleted vessels (which may still cast ok)
	for (i = 0; i < GetNativeRenderContext().world->nVessel(); i++) {
		if (body == GetNativeRenderContext().world->GetVessel(i))
			return body->Type();
	}

	return OBJTP_INVALID;
}

 bool oapiGetPause ()
{
	return !!GetNativeRenderContext().paused;
}

 const ATMCONST *oapiGetPlanetAtmConstants (OBJHANDLE hPlanet)
{
	return ((Planet*)hPlanet)->AtmParams ();
}

 void oapiGetPlanetAtmParams (OBJHANDLE hPlanet, double rad, ATMPARAM *prm)
{
	// This should operate directly on altitude
	Planet *planet = (Planet*)hPlanet;
	planet->GetAtmParam (rad - planet->Size(), 0, 0, prm);
}

 void oapiGetRotationMatrix (OBJHANDLE hObj, MATRIX3 *mat)
{
	if (((Body*)hObj)->s0) {
		const Matrix& m = ((Body*)hObj)->GRot();
		for (int i = 0; i < 9; i++) mat->data[i] = m.data[i];
	}
}

 bool oapiGetShowGrapplePoints ()
{
	return GetNativeRenderContext().showGrapple;
}

 double oapiGetSimStep ()
{
	return GetNativeRenderContext().time->SimDT;
}

 double oapiGetSimTime ()
{
	return GetNativeRenderContext().time->SimT0;
}

 double oapiGetSize (OBJHANDLE hObj)
{
	return ((Body*)hObj)->Size();
}

 oapi::Sketchpad *oapiGetSketchpad (SURFHANDLE surf)
{
	NativeGraphics *gc = GetNativeRenderContext().graphics;
	oapi::Sketchpad *skp = NULL;
	if (gc && surf) skp = gc->AcquireSketchpad (surf);
	return skp;
}

 double oapiGetSysTime ()
{
	return GetNativeRenderContext().time->SysT0;
}

 SURFHANDLE oapiGetTextureHandle (MESHHANDLE hMesh, oapi::UInt32 texidx)
{
	Mesh *mesh = (Mesh*)hMesh;
	return (mesh ? mesh->GetTexture (texidx-1) : 0);
}

 VESSEL *oapiGetVesselInterface (OBJHANDLE hVessel)
{
	if (((Body*)hVessel)->Type() != OBJTP_VESSEL) return 0;
	else return ((Vessel*)hVessel)->GetModuleInterface();
}

 VECTOR3 oapiGetWindVector (OBJHANDLE hPlanet, double lng, double lat, double alt, int frame, double *windspeed)
{
	return MakeVECTOR3 (((Planet*)hPlanet)->WindVelocity (lng, lat, alt, frame, 0, windspeed));
}

 void oapiGlobalToEqu (OBJHANDLE hObj, const VECTOR3 &glob, double *lng, double *lat, double *rad)
{
	if (((Body*)hObj)->s0) {
		Vector vglob(glob.x, glob.y, glob.z);
		((Body*)hObj)->GlobalToEquatorial(vglob, *lng, *lat, *rad);
	}
}

 MESHHANDLE oapiLoadMesh (const char *fname)
{
	// Retain the original optional SDK load behavior (e.g. invisible small-body
    // shape probes). Required vessel meshes use the strict MeshServices loader.
    const auto* resources=GetNativeRenderContext().meshFiles;
    const std::string relative=ResourceResolver::Normalize(std::string(fname)+".msh");
    ifstream ifs(resources->Contains(relative)?resources->Resolve(relative):resources->Root()/relative);
	Mesh *mesh = new Mesh; GetRigidBodyServices().TraceAllocation(__FILE__,__LINE__);
	ifs >> *mesh;
	return (MESHHANDLE)mesh;
}

 const MESHHANDLE oapiLoadMeshGlobal (const char *fname)
{
	auto mesh=GetVesselServices().Meshes().LoadMesh(fname);
	if(GetNativeRenderContext().graphics) GetNativeRenderContext().graphics->StoreMesh((MESHHANDLE)mesh,fname);
	return (const MESHHANDLE)mesh;
}

 void oapiLocalToEqu (OBJHANDLE hObj, const VECTOR3 &loc, double *lng, double *lat, double *rad)
{
	if (((Body*)hObj)->s0) {
		Vector vloc(loc.x, loc.y, loc.z);
		((Body*)hObj)->LocalToEquatorial(vloc, *lng, *lat, *rad);
	}
}

 MESHGROUP *oapiMeshGroup (MESHHANDLE hMesh, oapi::UInt32 idx)
{
	if (!hMesh) {
		static bool errecho = true;
		if (errecho) {
			RenderLog("Invalid mesh handle. Returned NULL. (Continuing)");
			errecho = false;
		}
		return 0;
	}
	return (MESHGROUP*)(((Mesh*)hMesh)->GetGroup (idx));
}

 oapi::UInt32 oapiMeshGroupCount (MESHHANDLE hMesh)
{
	if (!hMesh) {
		static bool errecho = true;
		if (errecho) {
			RenderLog("Invalid mesh handle. Returned 0. (Continuing)");
			errecho = false;
		}
		return 0;
	}
	return ((Mesh*)hMesh)->nGroup();
}

 MESHGROUPEX *oapiMeshGroupEx (MESHHANDLE hMesh, oapi::UInt32 idx)
{
	return (MESHGROUPEX*)(((Mesh*)hMesh)->GetGroup (idx));
}

 MATERIAL *oapiMeshMaterial (MESHHANDLE hMesh, oapi::UInt32 idx)
{
	return ((Mesh*)hMesh)->GetMaterial (idx);
}

 oapi::UInt32 oapiMeshMaterialCount (MESHHANDLE hMesh)
{
	return ((Mesh*)hMesh)->nMaterial();
}

 oapi::UInt32 oapiMeshTextureCount (MESHHANDLE hMesh)
{
	return ((Mesh*)hMesh)->nTexture();
}

 bool oapiPlanetHasAtmosphere (OBJHANDLE hPlanet)
{
	return ((Planet*)hPlanet)->HasAtmosphere();
}

 void oapiReleaseFont (oapi::Font *font)
{
	NativeGraphics *gc = GetNativeRenderContext().graphics;
	if (gc) gc->ReleaseFontResource (font);
}

 void oapiReleasePen (oapi::Pen *pen)
{
	NativeGraphics *gc = GetNativeRenderContext().graphics;
	if (gc) gc->ReleasePenResource (pen);
}

 void oapiReleaseSketchpad (oapi::Sketchpad *skp)
{
	NativeGraphics *gc = GetNativeRenderContext().graphics;
	if (gc && skp) gc->ReleaseSketchpadResource (skp);
}

 double oapiSurfaceElevation (OBJHANDLE hPlanet, double lng, double lat)
{
	Body *body = (Body*)hPlanet;
	if (body->Type() != OBJTP_PLANET) return 0.0;
	Planet *planet = (Planet*)body;
	ElevationManager *emgr = planet->ElevMgr();
	return (emgr ? emgr->Elevation (lat, lng) : 0.0);
}

 void oapiWriteLog (char *line)
{
	RenderLog (line);
}

oapi::Font* oapiCreateFont(int height,bool prop,const char* face,FontStyle style,int orientation)
{return GetNativeRenderContext().graphics->CreateFontResource(height,prop,face,style,orientation);}
void oapiAddNotification(NativeNotification type,const char* title,const char* message)
{std::clog<<title<<": "<<message<<'\n';}
namespace orbiter::production {
namespace {NativeRenderContext* current=nullptr;}
NativeRenderContext* BindNativeRenderContext(NativeRenderContext* next)
{auto* old=current;current=next;return old;}
NativeRenderContext& GetNativeRenderContext()
{if(!current) throw std::logic_error("Native production render context is unbound");return *current;}
const void* RenderConfig(oapi::UInt32 id) {return GetNativeRenderContext().configuration->GetParam(id);}
bool RenderTexturePath(const char* name,char* path,bool planet)
{
    const auto* resources=planet?GetNativeRenderContext().planetTextures:GetNativeRenderContext().textures;
    if(!resources) throw std::logic_error("Native texture resources are unbound");
    std::filesystem::path result;
    if(!planet && GetNativeRenderContext().highTextures && GetNativeRenderContext().highTextures->Contains(name)) {result=GetNativeRenderContext().highTextures->Resolve(name);const auto text=result.string();if(text.size()>=256)throw std::runtime_error("Texture path too long");std::strcpy(path,text.c_str());return true;}
    if(resources->Contains(name)) result=resources->Resolve(name);
    else if(resources->ContainsDirectory(name)) result=resources->ResolveDirectory(name);
    else if(planet) result=resources->Root()/ResourceResolver::Normalize(name);
    else return false;
    const auto text=result.string();if(text.size()>=256) throw std::runtime_error("Renderer asset path exceeds its buffer contract");
    std::strcpy(path,text.c_str());return true;
}
void RenderRegisterVisual(OBJHANDLE object,VISHANDLE visual) {static_cast<Body*>(object)->RegisterVisual(visual);}
void RenderUnregisterVisual(OBJHANDLE object) {static_cast<Body*>(object)->UnregisterVisual();}
oapi::UInt32 RenderBaseTiles(OBJHANDLE object,const SurftileSpec** tiles) {return static_cast<Base*>(object)->GetTileList(tiles);}
void RenderBaseStructures(OBJHANDLE object,MESHHANDLE** a,oapi::UInt32* na,MESHHANDLE** b,oapi::UInt32* nb)
{static_cast<Base*>(object)->ExportBaseStructures(reinterpret_cast<Mesh***>(a),na,reinterpret_cast<Mesh***>(b),nb);}
void RenderBaseShadows(OBJHANDLE object,MESHHANDLE** mesh,double** elevations,oapi::UInt32* count)
{static_cast<Base*>(object)->ExportShadowGeometry(reinterpret_cast<Mesh***>(mesh),elevations,count);}
bool RenderElevationGrid(ELEVHANDLE handle,int a,int b,int c,int d,int e,int f,std::int16_t* parent,float* result,double* mean)
{if(!handle)return false;static_cast<ElevationManager*>(handle)->ElevationGrid(a,b,c,d,e,f,parent,result,mean);return true;}
bool RenderElevationGrid(ELEVHANDLE handle,int a,int b,int c,int d,int e,int f,std::int16_t* parent,std::int16_t* result,double* mean)
{if(!handle)return false;static_cast<ElevationManager*>(handle)->ElevationGrid(a,b,c,d,e,f,parent,result,mean);return true;}
const std::vector<SceneLabelList>& RenderCelestialMarkers() {return GetNativeRenderContext().world->LabelList();}
oapi::UInt32 RenderSurfaceMarkers(OBJHANDLE object,const SceneLabelList** lists)
{int count;*lists=static_cast<Planet*>(object)->LabelList(&count);return count;}
oapi::UInt32 RenderSurfaceLegend(OBJHANDLE object,const SceneLabelType** types)
{auto* planet=static_cast<Planet*>(object);*types=planet->LabelLegend();return planet->NumLabelLegend();}
void RenderDetachParticle(OBJHANDLE vessel,oapi::ParticleStream* stream) {static_cast<Vessel*>(vessel)->DelParticleStream(stream);}
bool RenderHasCelestialModule(OBJHANDLE body) {return GetCelestialServices().HasModule(*static_cast<CelestialBody*>(body));}
OBJHANDLE RenderCelestialParent(OBJHANDLE body) {return const_cast<CelestialBody*>(static_cast<CelestialBody*>(body)->Primary());}
}

OBJHANDLE oapiGetGbodyByName (char *name)
{
	return (GetNativeRenderContext().world ? GetNativeRenderContext().world->GetGravObj (name, true) : 0);
}

double oapiGetPlanetObliquity (OBJHANDLE hPlanet)
{
	return ((Planet*)hPlanet)->Obliquity();
}

double oapiGetPlanetTheta (OBJHANDLE hPlanet)
{
	return ((Planet*)hPlanet)->EqLng();
}
