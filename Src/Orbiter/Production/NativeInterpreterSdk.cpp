// Copyright (c) Martin Schweiger
// Licensed under the MIT License
#include "NativeInterpreterSdk.h"
#include "NativeGraphics.h"
#include "NativeHelp.h"
#include "VesselServices.h"
#include "VesselLifetime.h"
#include "GeometryConversions.h"
#include "Text.h"
#include "Astro.h"
#include "Camera.h"
#include "Mesh.h"
#include "Planet.h"
#include "Config.h"
#include "TimeData.h"
#include "elevmgr.h"
#include <algorithm>
#include <cstdarg>
#include <cstdio>
#include <fstream>
#include <iostream>
#include <zlib.h>

using namespace orbiter::production;
namespace {
NativeRenderContext& context() { return GetNativeRenderContext(); }
ScriptApplication& application()
{
    if (!context().scriptApplication) throw std::logic_error("No active script application");
    return *context().scriptApplication;
}
}

int oapiGetOrbiterVersion()
{
    static const int buildDate = [] {
        const char *months[] = {"Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"};
        char ms[4];
        int day, year, month;
        std::sscanf(__DATE__, "%3s%d%d", ms, &day, &year);
        for (month=0; month<12; ++month) if (!ComparePrefix(ms,months[month],3)) break;
        return (year%100)*10000 + (month+1)*100 + day;
    }();
    return buildDate;
}

void oapiGetViewportSize(oapi::UInt32 *w, oapi::UInt32 *h, oapi::UInt32 *bpp)
{
    context().graphics->clbkGetViewportSize(w,h);
    if (bpp) *bpp=32; // native window and cockpit use the 32-bit RGBA framebuffer
}

SURFHANDLE oapiRegisterExhaustTexture(char *name) { return oapiRegisterParticleTexture(name); }
SURFHANDLE oapiRegisterReentryTexture(char *name) { return oapiRegisterParticleTexture(name); }
OBJHANDLE oapiCameraTarget() { return context().camera->Target(); }
void oapiCameraSetAperture(double aperture)
{
    application().SetScriptFOV(std::clamp(aperture, RAD*0.1, RAD*80.0));
}
void oapiCameraAttach(OBJHANDLE obj,int mode) { context().lifetime->SetView(static_cast<Body*>(obj),mode); }
bool oapiSetCameraMode(const CameraMode &mode) { context().camera->SetCMode(&mode); return true; }
bool oapiMoveGroundCamera(double forward,double right,double up)
{
    if (context().camera->GetMode()!=CAM_GROUNDOBSERVER) return false;
    context().camera->GroundObserverShift(right,forward,up);
    return true;
}
void oapiGetPlanetAtmParams(OBJHANDLE planet,double alt,double lng,double lat,ATMPARAM *prm)
{ static_cast<Planet*>(planet)->GetAtmParam(alt,lng,lat,prm); }
double oapiSurfaceElevationEx(OBJHANDLE body,double lng,double lat,int target,std::vector<ElevationTile>* cache,VECTOR3 *nml,int *lvl)
{
    if (static_cast<Body*>(body)->Type()!=OBJTP_PLANET) return 0.0;
    auto *manager=static_cast<Planet*>(body)->ElevMgr();
    Vector normal;
    if (nml) normal=MakeVector(*nml);
    double elevation=manager ? manager->Elevation(lat,lng,target,cache,nml ? &normal : nullptr,lvl) : 0.0;
    if (nml) *nml=MakeVECTOR3(normal);
    return elevation;
}
std::vector<ElevationTile>* InitTileCache(int size) { return new std::vector<ElevationTile>(size); }
void ReleaseTileCache(std::vector<ElevationTile>* cache) { delete cache; }
double oapiGetSysMJD() { return MJD(time(nullptr)) + UTC_CT_diff*day; }
bool oapiSetSimMJD(double mjd,int pmode) { return application().Jump(mjd,pmode); }
void oapiSetTimeAcceleration(double warp) { GetVesselServices().SetWarpFactor(warp); }
void oapiSetPause(bool pause) { application().Pause(pause); }
bool oapiSetTexture(MESHHANDLE mesh,oapi::UInt32 texidx,SURFHANDLE tex)
{ return static_cast<Mesh*>(mesh)->SetTexture(texidx-1,tex); }
int oapiSetMaterialEx(DEVMESHHANDLE mesh,oapi::UInt32 index,MatProp prop,const oapi::FVECTOR4* value)
{
    auto *gc=context().graphics;
    return gc ? gc->clbkSetMeshMaterialEx(mesh,index,prop,value) : 1;
}
bool oapiSetMeshProperty(MESHHANDLE mesh,oapi::UInt32 prop,oapi::UInt32 value)
{
    if (prop!=MESHPROPERTY_MODULATEMATALPHA) return false;
    static_cast<Mesh*>(mesh)->EnableMatAlpha(value!=0);
    return true;
}
bool oapiSetMeshProperty(DEVMESHHANDLE mesh,oapi::UInt32 prop,oapi::UInt32 value)
{
    auto *gc=context().graphics;
    return gc && gc->SetMeshProperty(mesh,prop,value);
}
bool oapiSaveSurface(const char *fname,SURFHANDLE surface,oapi::ImageFileFormat format,float quality)
{
    auto *gc=context().graphics;
    return gc && fname && gc->clbkSaveSurfaceToImage(surface,fname,format,quality);
}

oapi::UInt32 oapiGetMainMenuVisibilityMode() { return context().configuration->CfgUIPrm.MenuMode; }
void oapiSetMainMenuVisibilityMode(oapi::UInt32 mode) { context().configuration->CfgUIPrm.MenuMode=mode; }
oapi::UInt32 oapiGetMainInfoVisibilityMode() { return context().configuration->CfgUIPrm.InfoMode; }
void oapiSetMainInfoVisibilityMode(oapi::UInt32 mode) { context().configuration->CfgUIPrm.InfoMode=mode; }

bool oapiSimulateBufferedKey(oapi::UInt32 key,oapi::UInt32 *mod,oapi::UInt32 count,bool runningOnly)
{ return application().BufferedKey(key,mod,count,runningOnly); }
bool oapiSimulateImmediateKey(char keys[256],bool runningOnly)
{ return application().ImmediateKeys(keys,runningOnly); }
const char *oapiGetKeyState() { return application().KeyState(); }
bool oapiAcceptDelayedKey(char key,double interval)
{
    static char lastkey=static_cast<char>(255);
    static double lasttime=0;
    double now=context().time->SysT0;
    if (key==lastkey && now-lasttime<interval && now>lasttime) return false;
    lastkey=key;
    lasttime=now;
    return true;
}

oapi::UInt32 oapiDeflate(const std::uint8_t *input,oapi::UInt32 inputSize,std::uint8_t *output,oapi::UInt32 outputSize)
{
    z_stream stream{};
    if (deflateInit(&stream,Z_DEFAULT_COMPRESSION)!=Z_OK) return 0;
    stream.next_in=const_cast<Bytef*>(input);
    stream.avail_in=inputSize;
    stream.next_out=output;
    stream.avail_out=outputSize;
    const int status=deflate(&stream,Z_FINISH);
    const auto written=status==Z_STREAM_END ? outputSize-stream.avail_out : 0;
    deflateEnd(&stream);
    return written;
}
oapi::UInt32 oapiInflate(const std::uint8_t *input,oapi::UInt32 inputSize,std::uint8_t *output,oapi::UInt32 outputSize)
{
    uLongf written=outputSize;
    return uncompress(output,&written,input,inputSize)==Z_OK ? static_cast<oapi::UInt32>(written) : 0;
}

void __writeLogError(const char *func,const char *file,int line,const char *format,...)
{
    std::fprintf(stderr,"%s (%s:%d): ",func,file,line);
    va_list args;
    va_start(args,format);
    std::vfprintf(stderr,format,args);
    va_end(args);
    std::fputc('\n',stderr);
}
bool oapiOpenHelp(HELPCONTEXT *help)
{
    try {
        const auto& render=context();
        if(!render.programFiles)throw std::runtime_error("Help resources are not bound");
        const auto& files=*render.programFiles;
        auto url=NativeHelpUrl(files,help&&help->helpfile?help->helpfile:"html/orbiter.chm",help&&help->topic?help->topic:"");
        // The original vessel/scenario metadata names the contextual help book.
        // Resolve optional contexts independently so an unavailable add-on does
        // not prevent opening the requested stock topic.
        for(bool vessel:{true,false}) {
            const char* metadata=vessel?(render.focus?render.focus->HelpContext():nullptr):render.scenarioHelp.c_str();
            if(!metadata||!*metadata)continue;
            try {
                auto target=NativeContextHelpUrl(files,metadata,vessel);
                static const char hex[]="0123456789ABCDEF";
                url+=vessel?"&vessel=":"&scenario=";
                for(unsigned char c:target) {url+='%';url+=hex[c>>4];url+=hex[c&15];}
            } catch(const std::exception& error) {std::clog<<"Context help: "<<error.what()<<'\n';}
        }
        OpenNativeHelp(url);
        return true;
    } catch(const std::exception& error) {
        std::clog<<"Help: "<<error.what()<<'\n';
        oapiAddNotification(OAPINOTIF_ERROR,"Orbiter Help",error.what());
        return false;
    }
}

int oapiEditMeshGroup (MESHHANDLE hMesh, oapi::UInt32 grpidx, GROUPEDITSPEC *ges)
{
	Mesh* mesh=(Mesh*)hMesh;
	if (grpidx>=mesh->nGroup()) return 1;
	orbiter::production::MeshGroupEdit edit{};
	edit.flags=ges->flags;
	if (ges->flags & (GRPEDIT_SETUSERFLAG|GRPEDIT_ADDUSERFLAG|GRPEDIT_DELUSERFLAG)) edit.UsrFlag=ges->UsrFlag;
	if (ges->flags & GRPEDIT_VTXMOD) {
		edit.nVtx=ges->nVtx;
		if (edit.nVtx) { edit.Vtx=ges->Vtx; edit.vIdx=ges->vIdx; }
	}
	return ((Mesh*)hMesh)->EditGroup (grpidx, &edit);
}

namespace {
std::filesystem::path outputPath(PathRoot root, const std::string& name)
{
    const char *folders[]={"root","config","","textures","textures2","meshes","modules"};
    if (root<ROOT || root>MODULES) throw std::invalid_argument("Unknown script file root");
    auto base=context().scriptSaveDirectory;
    if (root!=SCENARIOS) base=base/"ScriptFiles"/folders[root];
    auto path=base/ResourceResolver::Normalize(name);
    // User files may be created between reads, so validate their current path
    // rather than using the immutable stock file index for writable files.
    auto relative=std::filesystem::weakly_canonical(path).lexically_relative(std::filesystem::weakly_canonical(base));
    if (relative.empty() || *relative.begin()=="..") throw std::invalid_argument("Script file escapes its root");
    return path;
}
std::string fileName(PathRoot root,const char *name)
{
    switch(root) {
    case SCENARIOS:return std::string(name)+".scn";
    case TEXTURES:case TEXTURES2:return std::string(name)+".dds";
    case MESHES:return std::string(name)+".msh";
    default:return name;
    }
}
std::filesystem::path stockFile(PathRoot root,std::string name)
{
    const auto &c=context();
    auto *index=c.programFiles;
    switch(root) {
    case CONFIG:index=c.configurationFiles;break;
    case TEXTURES:index=c.textures;break;
    case TEXTURES2:index=c.highTextures;break;
    case MESHES:index=c.meshFiles;break;
    case SCENARIOS:name="Scenarios/"+name;break;
    case MODULES:name="Modules/"+name;break;
    default:break;
    }
    return index && index->Contains(name) ? index->Resolve(name) : std::filesystem::path();
}
}
FILEHANDLE oapiOpenFile(const char *name, FileAccessMode mode, PathRoot root)
{
    if (!name) return nullptr;
    try {
        const auto relative=fileName(root,name);
        auto path=outputPath(root,relative);
        if (mode==FILE_IN || mode==FILE_IN_ZEROONFAIL) {
            if (!std::filesystem::exists(path)) path=stockFile(root,relative);
            auto stream=std::make_unique<std::ifstream>(path);
            if (mode==FILE_IN_ZEROONFAIL && !*stream) return nullptr;
            return stream.release();
        }
        if (mode!=FILE_APP && mode!=FILE_OUT) return nullptr;
        std::filesystem::create_directories(path.parent_path());
        if (mode==FILE_APP && !std::filesystem::exists(path)) {
            auto original=stockFile(root,relative);
            if (!original.empty()) std::filesystem::copy_file(original,path);
        }
        return new std::ofstream(path,mode==FILE_APP ? std::ios::app : std::ios::out);
    } catch (const std::exception& e) {
        std::clog<<"Cannot open script file: "<<e.what()<<'\n';
        return nullptr;
    }
}
void oapiCloseFile(FILEHANDLE file,FileAccessMode mode)
{
    if (mode==FILE_IN || mode==FILE_IN_ZEROONFAIL) delete static_cast<std::ifstream*>(file);
    else if (mode==FILE_OUT || mode==FILE_APP) delete static_cast<std::ofstream*>(file);
}
void oapiWriteLine(FILEHANDLE file,char *line) { *static_cast<std::ofstream*>(file)<<line<<std::endl; }
bool oapiSaveScenario(const char *name,const char *desc)
{
    try {
        auto path=outputPath(SCENARIOS,fileName(SCENARIOS,name));
        return application().SaveScriptScenario(path.string().c_str(),desc);
    } catch (const std::exception& e) {
        std::clog<<"Cannot save script scenario: "<<e.what()<<'\n';
        return false;
    }
}
