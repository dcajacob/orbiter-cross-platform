#include "glad.h"
#include "Evidence.h"
#include "OGLClient.h"
#include <tlhelp32.h>
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
unsigned frames=0,draws=0,presents=0;
uint64_t indices=0;
std::ofstream events,assets;
std::set<std::string> seen;
std::map<std::string,unsigned> objectDraws;
std::string currentObject;
std::string name(OBJHANDLE h) { char value[256]{};oapiGetObjectName(h,value,sizeof(value));return value; }
std::ofstream output(const char *path) { std::ofstream f(path,std::ios::binary);f.imbue(std::locale::classic());f<<std::setprecision(17);if(!f)throw std::runtime_error("cannot write graphics evidence");return f; }
}
void Begin() {
    enabled=std::filesystem::is_regular_file("ogl-evidence.enabled");frames=draws=presents=0;indices=0;seen.clear();objectDraws.clear();currentObject.clear();
    if(!enabled)return;
    captured=false;
    events=output("visual-events.csv");events<<"frame,event,object,type\n";
    assets=output("loaded-assets.txt");
    auto info=output("renderer-info.json");
    info<<"{\"vendor\":"<<std::quoted(reinterpret_cast<const char *>(glGetString(GL_VENDOR)))
        <<",\"renderer\":"<<std::quoted(reinterpret_cast<const char *>(glGetString(GL_RENDERER)))
        <<",\"version\":"<<std::quoted(reinterpret_cast<const char *>(glGetString(GL_VERSION)))<<"}\n";

}
void Presented() { if(enabled)++presents; }
void End(bool contextDeleted) {
    if(!enabled)return;
    auto lifecycle=output("graphics-lifecycle.json");
    lifecycle<<"{\"rendered_frames\":"<<frames<<",\"successful_presents\":"<<presents
             <<",\"context_deleted\":"<<(contextDeleted?"true":"false")<<"}\n";
    events.close();assets.close();enabled=false;
}
void Visual(const char *event,OBJHANDLE object) {
    if(enabled){events<<frames<<','<<event<<','<<name(object)<<','<<oapiGetObjectType(object)<<'\n';events.flush();}
}
void Asset(const char *path) { if(enabled && path && seen.insert(path).second){assets<<path<<'\n';assets.flush();} }
void Object(OBJHANDLE object) { if(enabled)currentObject=object?name(object):std::string(); }
void Draw(unsigned vertices,unsigned count) { if(enabled){++draws;indices+=count;if(!currentObject.empty())++objectDraws[currentObject];} }
void Rendered() { if(enabled)++frames; }
void Frame() {
    if(!enabled || captured || frames!=50)return;
    captured=true;
    GLint viewport[4]{};glGetIntegerv(GL_VIEWPORT,viewport);
    if(viewport[2]!=1280 || viewport[3]!=720)throw std::runtime_error("unexpected real-client evidence viewport");
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
                auto mesh=v->GetMeshTemplate(j);
                scene<<name(h)<<",vessel,"<<v->GetClassName()<<",template,"<<j<<','<<v->GetMeshName(j)<<','
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
    auto summary=output("scene-summary.json");summary<<"{\"frames\":"<<frames<<",\"mesh_draw_calls\":"<<draws<<",\"indices\":"<<indices<<",\"width\":1280,\"height\":720}\n";
    auto objects=output("object-draws.csv");objects<<"object,mesh_draw_calls\n";
    for(auto &entry:objectDraws)objects<<entry.first<<','<<entry.second<<'\n';
    events.flush();assets.flush();
}
}
