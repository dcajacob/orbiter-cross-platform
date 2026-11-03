// Copyright (c) Martin Schweiger
// Licensed under the MIT License
#ifndef ORBITER_NATIVE_RENDER_API_H
#define ORBITER_NATIVE_RENDER_API_H
#include "Export.h"
#include "NativeGraphicsData.h"
#include "NavigationData.h"
#include "DrawAPI.h"
#include <cstdint>
using NAVDATA = orbiter::production::NavigationData;
ORBITER_PRODUCTION_API void oapiGetNavPos(NAVHANDLE,VECTOR3*);
ORBITER_PRODUCTION_API oapi::UInt32 oapiGetNavType(NAVHANDLE);
ORBITER_PRODUCTION_API int oapiGetNavData(NAVHANDLE,NAVDATA*);
ORBITER_PRODUCTION_API oapi::Brush* oapiCreateBrush(oapi::UInt32);
ORBITER_PRODUCTION_API void oapiReleaseBrush(oapi::Brush*);
ORBITER_PRODUCTION_API void oapiDestroySurface(SURFHANDLE);
ORBITER_PRODUCTION_API void oapiClearSurface(SURFHANDLE,oapi::UInt32=0);
ORBITER_PRODUCTION_API void oapiBlt(SURFHANDLE,SURFHANDLE,int,int,int,int,int,int,oapi::UInt32=SURF_NO_CK);
ORBITER_PRODUCTION_API double oapiCameraAperture ();
ORBITER_PRODUCTION_API void oapiCameraGlobalDir (VECTOR3 *gdir);
ORBITER_PRODUCTION_API void oapiCameraGlobalPos (VECTOR3 *gpos);
ORBITER_PRODUCTION_API bool oapiCameraInternal ();
ORBITER_PRODUCTION_API void oapiCameraSetCockpitDir(double polar, double azimuth, bool transition=false);
ORBITER_PRODUCTION_API SURFHANDLE oapiLoadTexture(const char *fname, bool dynamic=false);
ORBITER_PRODUCTION_API void oapiReleaseTexture(SURFHANDLE texture);
ORBITER_PRODUCTION_API SURFHANDLE oapiCreateSurfaceEx(int width, int height, oapi::UInt32 attrib);
ORBITER_PRODUCTION_API SURFHANDLE oapiRegisterParticleTexture(char *name);
ORBITER_PRODUCTION_API OBJHANDLE oapiCameraProxyGbody ();
ORBITER_PRODUCTION_API void oapiCameraRotationMatrix (MATRIX3 *rmat);
ORBITER_PRODUCTION_API int oapiCockpitMode ();
ORBITER_PRODUCTION_API oapi::Font *oapiCreateFont (int height, bool prop, char *face, FontStyle style);
ORBITER_PRODUCTION_API oapi::Pen *oapiCreatePen (int style, int width, oapi::UInt32 col);
ORBITER_PRODUCTION_API SURFHANDLE oapiCreateSurface (int width, int height);
ORBITER_PRODUCTION_API char *oapiDebugString ();
ORBITER_PRODUCTION_API void oapiDeleteMesh (MESHHANDLE hMesh);
ORBITER_PRODUCTION_API MESHHANDLE oapiCreateMesh(oapi::UInt32,MESHGROUP*);
ORBITER_PRODUCTION_API bool oapiAddMeshGroupBlock(MESHHANDLE,oapi::UInt32,const NTVERTEX*,oapi::UInt32,const oapi::UInt16*,oapi::UInt32);
ORBITER_PRODUCTION_API ELEVHANDLE oapiElevationManager (OBJHANDLE hPlanet);
ORBITER_PRODUCTION_API void oapiEquToLocal (OBJHANDLE hObj, double lng, double lat, double rad, VECTOR3 *loc);
ORBITER_PRODUCTION_API OBJHANDLE oapiGetBaseByIndex (OBJHANDLE hPlanet, int index);
ORBITER_PRODUCTION_API oapi::UInt32 oapiGetBaseCount (OBJHANDLE hPlanet);
ORBITER_PRODUCTION_API OBJHANDLE oapiGetBasePlanet (OBJHANDLE hBase);
ORBITER_PRODUCTION_API oapi::UInt32 oapiGetColour (oapi::UInt32 red, oapi::UInt32 green, oapi::UInt32 blue);
ORBITER_PRODUCTION_API OBJHANDLE oapiGetFocusObject ();
ORBITER_PRODUCTION_API OBJHANDLE oapiGetGbodyByIndex (int index);
ORBITER_PRODUCTION_API oapi::UInt32 oapiGetGbodyCount ();
ORBITER_PRODUCTION_API void oapiGetGlobalPos (OBJHANDLE hObj, VECTOR3 *pos);
ORBITER_PRODUCTION_API double oapiGetMass (OBJHANDLE hObj);
ORBITER_PRODUCTION_API const char* oapiGetMeshFilename(MESHHANDLE hMesh);
ORBITER_PRODUCTION_API int oapiGetMeshGroup (DEVMESHHANDLE hMesh, oapi::UInt32 grpidx, GROUPREQUESTSPEC *grs);
ORBITER_PRODUCTION_API int oapiEditMeshGroup (DEVMESHHANDLE hMesh, oapi::UInt32 grpidx, GROUPEDITSPEC *ges);
ORBITER_PRODUCTION_API bool oapiSetTexture (DEVMESHHANDLE hMesh, oapi::UInt32 texidx, SURFHANDLE tex);
ORBITER_PRODUCTION_API int oapiSetMaterial (DEVMESHHANDLE hMesh, oapi::UInt32 matidx, const MATERIAL *mat);
ORBITER_PRODUCTION_API OBJHANDLE oapiGetObjectByIndex (int index);
ORBITER_PRODUCTION_API oapi::UInt32 oapiGetObjectCount ();
ORBITER_PRODUCTION_API void oapiGetObjectName (OBJHANDLE hObj, char *name, int n);
ORBITER_PRODUCTION_API const void *oapiGetObjectParam (OBJHANDLE hObj, oapi::UInt32 paramtype);
ORBITER_PRODUCTION_API int oapiGetObjectType (OBJHANDLE hObj);
ORBITER_PRODUCTION_API bool oapiGetPause ();
ORBITER_PRODUCTION_API const ATMCONST *oapiGetPlanetAtmConstants (OBJHANDLE hPlanet);
ORBITER_PRODUCTION_API void oapiGetPlanetAtmParams (OBJHANDLE hPlanet, double rad, ATMPARAM *prm);
ORBITER_PRODUCTION_API void oapiGetRotationMatrix (OBJHANDLE hObj, MATRIX3 *mat);
ORBITER_PRODUCTION_API bool oapiGetShowGrapplePoints ();
ORBITER_PRODUCTION_API double oapiGetSimStep ();
ORBITER_PRODUCTION_API double oapiGetSimTime ();
ORBITER_PRODUCTION_API double oapiGetSize (OBJHANDLE hObj);
ORBITER_PRODUCTION_API oapi::Sketchpad *oapiGetSketchpad (SURFHANDLE surf);
ORBITER_PRODUCTION_API double oapiGetSysTime ();
ORBITER_PRODUCTION_API SURFHANDLE oapiGetTextureHandle (MESHHANDLE hMesh, oapi::UInt32 texidx);
ORBITER_PRODUCTION_API VESSEL *oapiGetVesselInterface (OBJHANDLE hVessel);
ORBITER_PRODUCTION_API VECTOR3 oapiGetWindVector (OBJHANDLE hPlanet, double lng, double lat, double alt, int frame=0, double *windspeed=nullptr);
ORBITER_PRODUCTION_API void oapiGlobalToEqu (OBJHANDLE hObj, const VECTOR3 &glob, double *lng, double *lat, double *rad);
ORBITER_PRODUCTION_API MESHHANDLE oapiLoadMesh (const char *fname);
ORBITER_PRODUCTION_API const MESHHANDLE oapiLoadMeshGlobal (const char *fname);
ORBITER_PRODUCTION_API void oapiLocalToEqu (OBJHANDLE hObj, const VECTOR3 &loc, double *lng, double *lat, double *rad);
ORBITER_PRODUCTION_API MESHGROUP *oapiMeshGroup (MESHHANDLE hMesh, oapi::UInt32 idx);
ORBITER_PRODUCTION_API oapi::UInt32 oapiMeshGroupCount (MESHHANDLE hMesh);
ORBITER_PRODUCTION_API MESHGROUPEX *oapiMeshGroupEx (MESHHANDLE hMesh, oapi::UInt32 idx);
ORBITER_PRODUCTION_API MATERIAL *oapiMeshMaterial (MESHHANDLE hMesh, oapi::UInt32 idx);
ORBITER_PRODUCTION_API oapi::UInt32 oapiMeshMaterialCount (MESHHANDLE hMesh);
ORBITER_PRODUCTION_API oapi::UInt32 oapiMeshTextureCount (MESHHANDLE hMesh);
ORBITER_PRODUCTION_API bool oapiPlanetHasAtmosphere (OBJHANDLE hPlanet);
ORBITER_PRODUCTION_API void oapiReleaseFont (oapi::Font *font);
ORBITER_PRODUCTION_API void oapiReleasePen (oapi::Pen *pen);
ORBITER_PRODUCTION_API void oapiReleaseSketchpad (oapi::Sketchpad *skp);
ORBITER_PRODUCTION_API double oapiSurfaceElevation (OBJHANDLE hPlanet, double lng, double lat);
ORBITER_PRODUCTION_API void oapiWriteLog (char *line);
ORBITER_PRODUCTION_API oapi::Font* oapiCreateFont(int,bool,const char*,FontStyle=FONT_NORMAL,int=0);
enum NativeNotification {OAPINOTIF_SUCCESS,OAPINOTIF_ERROR};
ORBITER_PRODUCTION_API void oapiAddNotification(NativeNotification,const char*,const char*);
ORBITER_PRODUCTION_API OBJHANDLE oapiGetGbodyByName (char *name);
ORBITER_PRODUCTION_API double oapiGetPlanetObliquity (OBJHANDLE hPlanet);
ORBITER_PRODUCTION_API double oapiGetPlanetTheta (OBJHANDLE hPlanet);
#endif
