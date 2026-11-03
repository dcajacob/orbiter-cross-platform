#include "glad.h"
#include "Evidence.h"
#include "InstrumentEvidence.h"
#include "OGLClient.h"
#include "MeshManager.h"
#include <tlhelp32.h>
#include <dbghelp.h>
#include <cstdio>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <locale>
#include <set>
#include <map>
#include <stdexcept>
#include <vector>

namespace Evidence {
namespace {
bool enabled=false,captured=false;
PVOID faultHandler=nullptr;
unsigned frames=0,draws=0,presents=0;
uint64_t indices=0;
std::ofstream events,assets;
std::set<std::string> seen;
std::map<std::string,unsigned> objectDraws;
std::string currentObject;
std::map<std::string,std::pair<unsigned,uint64_t>> planetTiles;
std::map<std::pair<std::string,int>,uint64_t> archiveReads;
std::string name(OBJHANDLE h) { char value[256]{};oapiGetObjectName(h,value,sizeof(value));return value; }
std::ofstream output(const char *path) { std::ofstream f(path,std::ios::binary);f.imbue(std::locale::classic());f<<std::setprecision(17);if(!f)throw std::runtime_error("cannot write graphics evidence");return f; }
LONG CALLBACK fault(EXCEPTION_POINTERS *exception) {
    if(exception->ExceptionRecord->ExceptionCode!=EXCEPTION_ACCESS_VIOLATION)return EXCEPTION_CONTINUE_SEARCH;
    FILE *log=fopen("graphics-fault.txt","w");if(!log)return EXCEPTION_CONTINUE_SEARCH;
    HANDLE process=GetCurrentProcess();SymSetOptions(SYMOPT_LOAD_LINES|SYMOPT_UNDNAME);SymInitialize(process,nullptr,TRUE);
    CONTEXT context=*exception->ContextRecord;STACKFRAME64 frame{};
    frame.AddrPC.Offset=context.Rip;frame.AddrStack.Offset=context.Rsp;frame.AddrFrame.Offset=context.Rbp;
    frame.AddrPC.Mode=frame.AddrStack.Mode=frame.AddrFrame.Mode=AddrModeFlat;
    for(int i=0;i<40 && frame.AddrPC.Offset;++i) {
        DWORD64 address=frame.AddrPC.Offset,offset=0;
        char buffer[sizeof(SYMBOL_INFO)+MAX_SYM_NAME]{};auto symbol=reinterpret_cast<SYMBOL_INFO *>(buffer);
        symbol->SizeOfStruct=sizeof(SYMBOL_INFO);symbol->MaxNameLen=MAX_SYM_NAME;
        IMAGEHLP_LINE64 line{};line.SizeOfStruct=sizeof(line);DWORD displacement=0;
        MEMORY_BASIC_INFORMATION region{};VirtualQuery(reinterpret_cast<void *>(address),&region,sizeof(region));
        char module[MAX_PATH]{};GetModuleFileNameA(reinterpret_cast<HMODULE>(region.AllocationBase),module,MAX_PATH);
        fprintf(log,"%s+0x%llx",module,address-reinterpret_cast<uint64_t>(region.AllocationBase));
        if(SymFromAddr(process,address,&offset,symbol))fprintf(log," %s+0x%llx",symbol->Name,offset);
        if(SymGetLineFromAddr64(process,address,&displacement,&line))fprintf(log," %s:%lu",line.FileName,line.LineNumber);
        fprintf(log,"\n");fflush(log);
        if(!StackWalk64(IMAGE_FILE_MACHINE_AMD64,process,GetCurrentThread(),&frame,&context,nullptr,SymFunctionTableAccess64,SymGetModuleBase64,nullptr))break;
    }
    fclose(log);return EXCEPTION_CONTINUE_SEARCH;
}
void APIENTRY debugMessage(GLenum,GLenum type,GLuint,GLenum,GLsizei,const GLchar *message,const void *) {
    if(type!=GL_DEBUG_TYPE_ERROR)return;
    FILE *log=fopen("graphics-errors.txt","a");if(log){fprintf(log,"%s\n",message);fclose(log);}
}
}
void Begin() {
    InstrumentEvidence::Begin();
    enabled=std::filesystem::is_regular_file("ogl-evidence.enabled");frames=draws=presents=0;indices=0;seen.clear();objectDraws.clear();currentObject.clear();planetTiles.clear();archiveReads.clear();
    if(!enabled)return;
    captured=false;
    setvbuf(stdout,nullptr,_IONBF,0);
    faultHandler=AddVectoredExceptionHandler(1,fault);
    if(glDebugMessageCallback){glEnable(GL_DEBUG_OUTPUT);glEnable(GL_DEBUG_OUTPUT_SYNCHRONOUS);glDebugMessageCallback(debugMessage,nullptr);}
    events=output("visual-events.csv");events<<"frame,event,object,type\n";
    assets=output("loaded-assets.txt");
    RECT client{};GetClientRect(g_client->GetRenderWindow(),&client);
    auto info=output("renderer-info.json");
    info<<"{\"vendor\":"<<std::quoted(reinterpret_cast<const char *>(glGetString(GL_VENDOR)))
        <<",\"renderer\":"<<std::quoted(reinterpret_cast<const char *>(glGetString(GL_RENDERER)))
        <<",\"version\":"<<std::quoted(reinterpret_cast<const char *>(glGetString(GL_VERSION)))
        <<",\"client_width\":"<<client.right<<",\"client_height\":"<<client.bottom<<"}\n";

}
void Presented() { if(enabled)++presents; }
void End(bool contextDeleted) {
    InstrumentEvidence::End();
    if(!enabled)return;
    auto lifecycle=output("graphics-lifecycle.json");
    lifecycle<<"{\"rendered_frames\":"<<frames<<",\"successful_presents\":"<<presents
             <<",\"context_deleted\":"<<(contextDeleted?"true":"false")<<"}\n";
    if(faultHandler){RemoveVectoredExceptionHandler(faultHandler);faultHandler=nullptr;}
    events.close();assets.close();enabled=false;
}
void Visual(const char *event,OBJHANDLE object) {
    if(enabled){events<<frames<<','<<event<<','<<name(object)<<','<<oapiGetObjectType(object)<<'\n';events.flush();}
}
void Asset(const char *path) { if(enabled && path && seen.insert(path).second){assets<<path<<'\n';assets.flush();} }
void Object(OBJHANDLE object) { if(enabled)currentObject=object?name(object):std::string(); }
void Draw(unsigned vertices,unsigned count) { if(enabled){++draws;indices+=count;if(!currentObject.empty())++objectDraws[currentObject];} }
void PlanetTile(OBJHANDLE object,unsigned count) {
    if(enabled){auto &tile=planetTiles[name(object)];++tile.first;tile.second+=count;}
}
void ArchiveRead(const char *path,int layer,unsigned bytes) { if(enabled && bytes)archiveReads[{path,layer}]+=bytes; }
void Rendered() { if(enabled)++frames;InstrumentEvidence::Rendered(); }
void Frame() {
    InstrumentEvidence::Frame();
    if(InstrumentEvidence::CaptureFrame())for(int i=0;i<2;++i){
        auto* surface=static_cast<OGLTexture*>(g_client->GetMFDSurface(i));
        if(!surface)throw std::runtime_error("Required original MFD texture missing");
        InstrumentEvidence::Mfd(i,surface->m_TexId,surface->m_Width,surface->m_Height);
    }
    if(!enabled || captured || !frames || oapiGetSimTime()<12.5)return;
    if(std::abs(oapiGetSimTime()-12.5)>1e-12)throw std::runtime_error("missing finalized tick-50 render for graphics evidence");
    captured=true;
    GLint viewport[4]{};glGetIntegerv(GL_VIEWPORT,viewport);
    if(viewport[2]!=1280 || viewport[3]!=720)throw std::runtime_error("unexpected real-client evidence viewport: "+std::to_string(viewport[2])+"x"+std::to_string(viewport[3]));
    std::vector<unsigned char> pixels(size_t(viewport[2])*viewport[3]*4);
    glBindFramebuffer(GL_FRAMEBUFFER,0);glReadBuffer(GL_BACK);glPixelStorei(GL_PACK_ALIGNMENT,1);
    glReadPixels(0,0,viewport[2],viewport[3],GL_RGBA,GL_UNSIGNED_BYTE,pixels.data());
    if(glGetError()!=GL_NO_ERROR)throw std::runtime_error("OpenGL scene readback failed");
    auto image=output("scene.rgba");image.write(reinterpret_cast<const char *>(pixels.data()),pixels.size());
    auto scene=output("scene.csv");scene<<"object,type,class,mesh,index,name,groups,materials,textures,px,py,pz\n";
    for(DWORD i=0;i<oapiGetObjectCount();++i) {
        auto h=oapiGetObjectByIndex(i);VECTOR3 p{};oapiGetGlobalPos(h,&p);
        if(oapiGetObjectType(h)==OBJTP_VESSEL) {
            VESSEL *v=oapiGetVesselInterface(h);
            for(UINT j=0;j<v->GetMeshCount();++j) {
                struct OwnedMesh { MESHHANDLE value=nullptr;~OwnedMesh(){if(value)oapiDeleteMesh(value);} } owned;
                auto mesh=v->GetMeshTemplate(j);const char *meshName=v->GetMeshName(j);
                if(!mesh && !meshName)continue; // deleted vessel mesh slot
                if(mesh && !meshName)meshName=g_client->GetMeshManager()->GetMeshName(mesh);
                // Config-driven preloads bypass clbkStoreMeshPersistent, but the
                // current engine retains their parser-assigned filename.
                if(mesh && !meshName)meshName=oapiGetMeshFilename(mesh);
                bool preloaded=mesh!=nullptr;
                if(!mesh)mesh=owned.value=v->CopyMeshFromTemplate(j);
                if(!mesh || !meshName)throw std::runtime_error("stock mesh identity is unavailable for "+name(h));
                scene<<name(h)<<",vessel,"<<v->GetClassName()<<','<<(preloaded?"template":"on-demand")<<','<<j<<','<<meshName<<','
                     <<oapiMeshGroupCount(mesh)<<','<<oapiMeshMaterialCount(mesh)<<','<<oapiMeshTextureCount(mesh)<<','<<p.x<<','<<p.y<<','<<p.z<<'\n';
                for(DWORD k=1;k<=oapiMeshTextureCount(mesh);++k) {
                    auto texture=static_cast<OGLTexture *>(oapiGetTextureHandle(mesh,k));
                    if(!texture || texture->m_file.empty())throw std::runtime_error("required stock vessel texture failed to load");
                    Asset(texture->m_file.c_str());
                }
            }
        } else scene<<name(h)<<",celestial,,,,,,,,"<<p.x<<','<<p.y<<','<<p.z<<'\n';
    }
    auto modules=output("renderer-modules.txt");
    HANDLE snapshot=CreateToolhelp32Snapshot(TH32CS_SNAPMODULE|TH32CS_SNAPMODULE32,GetCurrentProcessId());
    if(snapshot==INVALID_HANDLE_VALUE)throw std::runtime_error("cannot inspect actual graphics DLL paths");
    MODULEENTRY32W module{};module.dwSize=sizeof(module);
    if(Module32FirstW(snapshot,&module))do {
        modules<<std::filesystem::path(module.szExePath).generic_u8string()<<'\n';
    }while(Module32NextW(snapshot,&module));
    CloseHandle(snapshot);
    auto camera=output("camera.csv");VECTOR3 p{},d{};MATRIX3 r{};
    oapiCameraGlobalPos(&p);oapiCameraGlobalDir(&d);oapiCameraRotationMatrix(&r);
    camera<<"px,py,pz,dx,dy,dz,aperture,m11,m12,m13,m21,m22,m23,m31,m32,m33\n"
          <<p.x<<','<<p.y<<','<<p.z<<','<<d.x<<','<<d.y<<','<<d.z<<','<<oapiCameraAperture();
    for(double value:r.data)camera<<','<<value;camera<<'\n';
    auto summary=output("scene-summary.json");summary<<"{\"frames\":"<<frames<<",\"simulation_seconds\":"<<oapiGetSimTime()<<",\"mesh_draw_calls\":"<<draws<<",\"indices\":"<<indices<<",\"width\":1280,\"height\":720}\n";
    auto objects=output("object-draws.csv");objects<<"object,mesh_draw_calls\n";
    for(auto &entry:objectDraws)objects<<entry.first<<','<<entry.second<<'\n';
    auto planets=output("planet-tiles.csv");planets<<"object,textured_draw_calls,indices\n";
    for(auto &entry:planetTiles)planets<<entry.first<<','<<entry.second.first<<','<<entry.second.second<<'\n';
    auto archives=output("archive-reads.csv");archives<<"path,layer,inflated_bytes\n";
    for(auto &entry:archiveReads)archives<<entry.first.first<<','<<entry.first.second<<','<<entry.second<<'\n';
    events.flush();assets.flush();
}
}
