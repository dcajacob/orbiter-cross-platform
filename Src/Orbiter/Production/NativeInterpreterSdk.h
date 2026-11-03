// Copyright (c) Martin Schweiger
// Licensed under the MIT License
#pragma once
#include "NativeRenderApi.h"
#include "NativeVesselAPI.h"
#include <vector>
#include <filesystem>
#include <exception>
typedef enum { FILE_IN, FILE_OUT, FILE_APP, FILE_IN_ZEROONFAIL } FileAccessMode;
typedef enum { ROOT, CONFIG, SCENARIOS, TEXTURES, TEXTURES2, MESHES, MODULES } PathRoot;
#define USRINPUT_NEEDANSWER 1
#define oapiWriteLogError(format, ...) __writeLogError(__FUNCTION__,__FILE__,__LINE__,format,__VA_ARGS__)
struct ElevationTile;
ORBITER_PRODUCTION_API int oapiGetOrbiterVersion ();
ORBITER_PRODUCTION_API void oapiGetViewportSize (oapi::UInt32 *w, oapi::UInt32 *h, oapi::UInt32 *bpp = 0);
ORBITER_PRODUCTION_API SURFHANDLE oapiRegisterExhaustTexture (char *name);
ORBITER_PRODUCTION_API SURFHANDLE oapiRegisterReentryTexture (char *name);
ORBITER_PRODUCTION_API OBJHANDLE oapiCameraTarget ();
ORBITER_PRODUCTION_API void oapiCameraSetAperture (double aperture);
ORBITER_PRODUCTION_API void oapiCameraAttach (OBJHANDLE hObj, int mode);
ORBITER_PRODUCTION_API bool oapiSetCameraMode(const CameraMode &mode);
ORBITER_PRODUCTION_API bool oapiMoveGroundCamera (double forward, double right=0, double up=0);
ORBITER_PRODUCTION_API void oapiGetPlanetAtmParams (OBJHANDLE hPlanet, double alt, double lng, double lat, ATMPARAM *prm);
ORBITER_PRODUCTION_API double oapiSurfaceElevationEx(OBJHANDLE hPlanet, double lng, double lat, int tgtlvl = 0, std::vector<ElevationTile> *tilecache = 0, VECTOR3 *nml = 0, int *lvl = 0);
ORBITER_PRODUCTION_API std::vector<ElevationTile> *InitTileCache(int size = 2);
ORBITER_PRODUCTION_API void ReleaseTileCache(std::vector<ElevationTile> *tilecache);
ORBITER_PRODUCTION_API double oapiGetSysMJD ();
ORBITER_PRODUCTION_API bool oapiSetSimMJD (double mjd, int pmode = 0);
ORBITER_PRODUCTION_API void oapiSetTimeAcceleration (double warp);
ORBITER_PRODUCTION_API void oapiSetPause (bool pause);
ORBITER_PRODUCTION_API bool oapiSetTexture (MESHHANDLE hMesh, oapi::UInt32 texidx, SURFHANDLE tex);
ORBITER_PRODUCTION_API int oapiSetMaterialEx(DEVMESHHANDLE hMesh, oapi::UInt32 matidx, MatProp prp, const oapi::FVECTOR4* in);
ORBITER_PRODUCTION_API bool oapiSetMeshProperty (MESHHANDLE hMesh, oapi::UInt32 property, oapi::UInt32 value);
ORBITER_PRODUCTION_API bool oapiSetMeshProperty (DEVMESHHANDLE hMesh, oapi::UInt32 property, oapi::UInt32 value);
ORBITER_PRODUCTION_API bool oapiSaveSurface(const char* fname, SURFHANDLE hSrf, oapi::ImageFileFormat fmt, float quality = 0.7f);
ORBITER_PRODUCTION_API bool oapiOpenHelp (HELPCONTEXT *hcontext);
ORBITER_PRODUCTION_API oapi::UInt32 oapiGetMainMenuVisibilityMode();
ORBITER_PRODUCTION_API void oapiSetMainMenuVisibilityMode (oapi::UInt32 mode);
ORBITER_PRODUCTION_API oapi::UInt32 oapiGetMainInfoVisibilityMode();
ORBITER_PRODUCTION_API void oapiSetMainInfoVisibilityMode (oapi::UInt32 mode);
ORBITER_PRODUCTION_API FILEHANDLE oapiOpenFile (const char *fname, FileAccessMode mode, PathRoot root = ROOT);
ORBITER_PRODUCTION_API void       oapiCloseFile (FILEHANDLE file, FileAccessMode mode);
ORBITER_PRODUCTION_API bool oapiSaveScenario (const char *fname, const char *desc);
ORBITER_PRODUCTION_API void oapiWriteLine (FILEHANDLE file, char *line);
ORBITER_PRODUCTION_API void __writeLogError(const char *func, const char *file, int line, const char *format, ...);
ORBITER_PRODUCTION_API oapi::UInt32 oapiDeflate (const std::uint8_t *ebuf, oapi::UInt32 nebuf, std::uint8_t *zbuf, oapi::UInt32 nzbuf);
ORBITER_PRODUCTION_API oapi::UInt32 oapiInflate (const std::uint8_t *zbuf, oapi::UInt32 nzbuf, std::uint8_t *ebuf, oapi::UInt32 nebuf);
ORBITER_PRODUCTION_API bool oapiSimulateBufferedKey (oapi::UInt32 key, oapi::UInt32 *mod = 0, oapi::UInt32 nmod = 0, bool onRunningOnly = false);
ORBITER_PRODUCTION_API bool oapiSimulateImmediateKey (char kstate[256], bool onRunningOnly = false);
ORBITER_PRODUCTION_API const char *oapiGetKeyState ();
ORBITER_PRODUCTION_API NOTEHANDLE oapiCreateAnnotation (bool exclusive, double size, const VECTOR3 &col);
ORBITER_PRODUCTION_API bool oapiDelAnnotation (NOTEHANDLE hNote);
ORBITER_PRODUCTION_API void oapiAnnotationSetPos (NOTEHANDLE hNote, double x1, double y1, double x2, double y2);
ORBITER_PRODUCTION_API void oapiAnnotationSetSize (NOTEHANDLE hNote, double size);
ORBITER_PRODUCTION_API void oapiAnnotationSetColour (NOTEHANDLE hNote, const VECTOR3 &col);
ORBITER_PRODUCTION_API void oapiAnnotationSetText (NOTEHANDLE hNote, char *note);
ORBITER_PRODUCTION_API bool       oapiAcceptDelayedKey (char key, double interval);
ORBITER_PRODUCTION_API int oapiEditMeshGroup(MESHHANDLE mesh, oapi::UInt32 idx, GROUPEDITSPEC *edit);
namespace orbiter::production {
// Internal native control flow, transported from a Lua worker by its existing
// exception handoff. The application catches it after Runtime has torn down.
class ORBITER_PRODUCTION_API ScriptProcessExit final : public std::exception {
public:
    explicit ScriptProcessExit(int code) noexcept : code(code) {}
    ~ScriptProcessExit() override;
    const char *what() const noexcept override;
    int code;
};
class ScriptApplication {
public:
    virtual ~ScriptApplication() = default;
    virtual bool Jump(double mjd, int mode) = 0;
    virtual void Quicksave() = 0;
    virtual void EndSession() = 0;
    virtual int RecorderStatus() const = 0;
    virtual bool ToggleRecorder(const char *name, bool overwrite = false) = 0;
    virtual void EndPlayback() = 0;
    virtual std::filesystem::path PlaybackFile(bool writing) = 0;
    virtual void SuspendPlayback() = 0;
    virtual void RescanPlayback() = 0;
    virtual void Pause(bool paused) = 0;
    virtual void SetScriptFOV(double aperture) = 0;
    virtual bool BufferedKey(oapi::UInt32 key, const oapi::UInt32 *modifiers, oapi::UInt32 count, bool runningOnly) = 0;
    virtual bool ImmediateKeys(const char *keys, bool runningOnly) = 0;
    virtual const char *KeyState() const = 0;
    virtual bool SaveScriptScenario(const char *name, const char *desc) = 0;
};
}
