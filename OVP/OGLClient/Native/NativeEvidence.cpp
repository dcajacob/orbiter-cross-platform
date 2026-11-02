// Licensed under the MIT License
// Actual native renderer evidence, same scene manifest/readback as Windows.
#include "glad.h"
#include "Evidence.h"
#include "OGLClient.h"
#include "MeshManager.h"
#include <cmath>
#include <fstream>
#include <iomanip>
#include <locale>
#include <set>
#include <map>
#include <vector>
#include <stdexcept>
namespace Evidence {
namespace {
bool enabled=false,captured=false;unsigned frames=0,draws=0,presents=0;uint64_t indices=0;
std::ofstream events,assets,visualMeshes;std::set<std::string> seen;std::map<std::string,unsigned> objectDraws;
std::string currentObject;std::map<std::string,std::pair<unsigned,uint64_t>> planetTiles;
std::map<std::pair<std::string,int>,uint64_t> archiveReads;
std::string name(OBJHANDLE h) {char value[256]{};oapiGetObjectName(h,value,sizeof(value));return value;}
std::ofstream output(const char* name) {
    std::ofstream result(GetNativeRenderContext().evidence/name,std::ios::binary);result.imbue(std::locale::classic());
    result.exceptions(std::ios::badbit|std::ios::failbit);result<<std::setprecision(17);return result;
}
}
void Begin() {
    enabled=!GetNativeRenderContext().evidence.empty();if(!enabled)return;
    std::filesystem::create_directories(GetNativeRenderContext().evidence);
    frames=draws=presents=0;indices=0;captured=false;seen.clear();objectDraws.clear();currentObject.clear();planetTiles.clear();archiveReads.clear();
    events=output("visual-events.csv");events<<"frame,event,object,type\n";assets=output("loaded-assets.txt");
    visualMeshes=output("visual-meshes.csv");visualMeshes<<"frame,object,class,module_version,index,name,groups,materials,textures,thrusters\n";
    int width,height;g_client->GetViewportSize(&width,&height);auto info=output("renderer-info.json");
    info<<"{\"vendor\":"<<std::quoted(reinterpret_cast<const char*>(glGetString(GL_VENDOR)))
        <<",\"renderer\":"<<std::quoted(reinterpret_cast<const char*>(glGetString(GL_RENDERER)))
        <<",\"version\":"<<std::quoted(reinterpret_cast<const char*>(glGetString(GL_VERSION)))
        <<",\"client_width\":"<<width<<",\"client_height\":"<<height<<"}\n";
}
void Presented() {if(enabled)++presents;}
void End(bool deleted) {
    if(!enabled)return;auto record=output("graphics-lifecycle.json");
    record<<"{\"rendered_frames\":"<<frames<<",\"successful_presents\":"<<presents<<",\"context_deleted\":"<<(deleted?"true":"false")<<"}\n";
    auto allDraws=output("object-draws-all.csv");allDraws<<"object,mesh_draw_calls\n";
    for(const auto& entry:objectDraws)allDraws<<entry.first<<','<<entry.second<<'\n';
    events.close();assets.close();visualMeshes.close();enabled=false;
}
void Visual(const char *event,OBJHANDLE object) {
    if(enabled){events<<frames<<','<<event<<','<<name(object)<<','<<oapiGetObjectType(object)<<'\n';events.flush();}
    if(enabled && std::string(event)=="register" && oapiGetObjectType(object)==OBJTP_VESSEL) {
        auto* vessel=oapiGetVesselInterface(object);
        for(oapi::UInt32 i=0;i<vessel->GetMeshCount();++i) {
            struct OwnedMesh {MESHHANDLE value=nullptr;~OwnedMesh(){if(value)oapiDeleteMesh(value);}} owned;
            auto mesh=vessel->GetMeshTemplate(i);
            const char* meshName=vessel->GetMeshName(i);
            if(!mesh)mesh=owned.value=vessel->CopyMeshFromTemplate(i);
            if(mesh && !meshName)meshName=oapiGetMeshFilename(mesh);
            if(!mesh)throw std::runtime_error("Lifecycle visual stock mesh is unavailable");
            if(!meshName)throw std::runtime_error("Lifecycle visual mesh identity is unavailable");
            visualMeshes<<frames<<','<<name(object)<<','<<vessel->GetClassName()<<','<<vessel->Version()<<','<<i<<','<<meshName<<','
                <<oapiMeshGroupCount(mesh)<<','<<oapiMeshMaterialCount(mesh)<<','<<oapiMeshTextureCount(mesh)<<','<<vessel->GetThrusterCount()<<'\n';
        }
        visualMeshes.flush();
    }
}
void Asset(const char *path) { if(enabled && path && seen.insert(path).second){assets<<path<<'\n';assets.flush();} }
void Object(OBJHANDLE object) { if(enabled)currentObject=object?name(object):std::string(); }
void Draw(unsigned vertices,unsigned count) { if(enabled){++draws;indices+=count;if(!currentObject.empty())++objectDraws[currentObject];} }
void PlanetTile(OBJHANDLE object,unsigned count) {
    if(enabled){auto &tile=planetTiles[name(object)];++tile.first;tile.second+=count;}
}
void ArchiveRead(const char *path,int layer,unsigned bytes) { if(enabled && bytes)archiveReads[{path,layer}]+=bytes; }
void Rendered() { if(enabled)++frames; }
void Frame() {
    if(!enabled || GetNativeRenderContext().captureTime<0 || captured || frames<50 || oapiGetSimTime()<GetNativeRenderContext().captureTime-1e-12)return;
    if(std::abs(oapiGetSimTime()-GetNativeRenderContext().captureTime)>1e-12)throw std::runtime_error("missing finalized tick-50 render for graphics evidence");
    captured=true;
    GLint viewport[4]{};glGetIntegerv(GL_VIEWPORT,viewport);
    if(viewport[2]!=1280 || viewport[3]!=720)throw std::runtime_error("unexpected real-client evidence viewport: "+std::to_string(viewport[2])+"x"+std::to_string(viewport[3]));
    std::vector<unsigned char> pixels(size_t(viewport[2])*viewport[3]*4);
    glBindFramebuffer(GL_FRAMEBUFFER,0);glReadBuffer(GL_BACK);glPixelStorei(GL_PACK_ALIGNMENT,1);
    glReadPixels(0,0,viewport[2],viewport[3],GL_RGBA,GL_UNSIGNED_BYTE,pixels.data());
    if(glGetError()!=GL_NO_ERROR)throw std::runtime_error("OpenGL scene readback failed");
    auto image=output("scene.rgba");image.write(reinterpret_cast<const char *>(pixels.data()),pixels.size());
    auto scene=output("scene.csv");scene<<"object,type,class,mesh,index,name,groups,materials,textures,px,py,pz\n";
    for(oapi::UInt32 i=0;i<oapiGetObjectCount();++i) {
        auto h=oapiGetObjectByIndex(i);VECTOR3 p{};oapiGetGlobalPos(h,&p);
        if(oapiGetObjectType(h)==OBJTP_VESSEL) {
            VESSEL *v=oapiGetVesselInterface(h);
            for(oapi::UInt j=0;j<v->GetMeshCount();++j) {
                struct OwnedMesh { MESHHANDLE value=nullptr;~OwnedMesh(){if(value)oapiDeleteMesh(value);} } owned;
                auto mesh=v->GetMeshTemplate(j);const char *meshName=v->GetMeshName(j);
                if(mesh && !meshName)meshName=g_client->GetMeshManager()->GetMeshName(mesh);
                // Config-driven preloads bypass clbkStoreMeshPersistent, but the
                // current engine retains their parser-assigned filename.
                if(mesh && !meshName)meshName=oapiGetMeshFilename(mesh);
                bool preloaded=mesh!=nullptr;
                if(!mesh)mesh=owned.value=v->CopyMeshFromTemplate(j);
                if(!mesh || !meshName)throw std::runtime_error("stock mesh identity is unavailable for "+name(h));
                scene<<name(h)<<",vessel,"<<v->GetClassName()<<','<<(preloaded?"template":"on-demand")<<','<<j<<','<<meshName<<','
                     <<oapiMeshGroupCount(mesh)<<','<<oapiMeshMaterialCount(mesh)<<','<<oapiMeshTextureCount(mesh)<<','<<p.x<<','<<p.y<<','<<p.z<<'\n';
                for(oapi::UInt32 k=1;k<=oapiMeshTextureCount(mesh);++k) {
                    auto texture=static_cast<OGLTexture *>(oapiGetTextureHandle(mesh,k));
                    if(!texture || texture->m_file.empty())throw std::runtime_error("required stock vessel texture failed to load");
                    Asset(texture->m_file.c_str());
                }
            }
        } else scene<<name(h)<<",celestial,,,,,,,,"<<p.x<<','<<p.y<<','<<p.z<<'\n';
    }
    auto modules=output("renderer-modules.txt");
    std::ifstream mappings("/proc/self/maps");std::string mapping;std::set<std::string> files;
    while(std::getline(mappings,mapping)) {auto slash=mapping.find('/');if(slash!=std::string::npos)files.insert(mapping.substr(slash));}
    for(const auto& file:files)modules<<file<<'\n';
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
