// Licensed under the MIT License
#include "glad.h"
#include "OGLClient.h"
#include "Scene.h"
#include "Renderer.h"
#include "OGLMesh.h"
#include "VObject.h"
#include "VStar.h"
#include "VVessel.h"
#include "TileMgr.h"
#include "tilemgr2.h"
#include "surfmgr2.h"
#include "SurfMgr.h"
#include "HazeMgr.h"
#include "RingMgr.h"
#include "CloudMgr.h"
#include "cloudmgr2.h"
#include "VBase.h"
#include "Particle.h"
#include "OGLPad.h"
#include "Evidence.h"
#include "RendererFiles.h"
#include "Production/NativeModule.h"
#include "Production/NativeAbi.h"
#include <GLFW/glfw3.h>
#include <filesystem>
#include <cstdio>
#include <cstring>
#include <iostream>
#include <memory>
#include <stdexcept>
namespace {
void require(bool valid,const char* text) {if(!valid) throw std::runtime_error(text);}
double scroll=0,lastX=0,lastY=0;bool dragging=false;
void error(int,const char* text) {std::cerr<<"GLFW: "<<text<<'\n';}
}
void OGLClient::Open()
{
    glfwSetErrorCallback(error);require(glfwInit()==GLFW_TRUE,"GLFW initialization failed");
    glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR,3);glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR,3);
    glfwWindowHint(GLFW_OPENGL_PROFILE,GLFW_OPENGL_CORE_PROFILE);
    glfwWindowHint(GLFW_SCALE_FRAMEBUFFER,GLFW_FALSE);
    nativeWindow=glfwCreateWindow(1280,720,"Orbiter: native production engine / Sol / ShuttlePB",nullptr,nullptr);
    require(nativeWindow!=nullptr,"Native OpenGL window creation failed");
    glfwMakeContextCurrent(nativeWindow);glfwSwapInterval(1);
    require(gladLoadGLLoader(reinterpret_cast<GLADloadproc>(glfwGetProcAddress))!=0,"Native OpenGL function loading failed");
    glfwSetScrollCallback(nativeWindow,[](GLFWwindow*,double,double y) {scroll+=y;});
    int width,height;glfwGetFramebufferSize(nativeWindow,&width,&height);m_width=width;m_height=height;
    Evidence::Begin();Renderer::GlobalInit(m_width,m_height);
    mTextureManager=std::make_unique<TextureManager>();mMeshManager=std::make_unique<OGLMeshManager>();
    mScene=std::make_unique<Scene>(m_width,m_height);
    TileManager::GlobalInit();HazeManager::GlobalInit();SurfTile::GlobalInit();
    SurfaceManager::GlobalInit();vBase::GlobalInit();OGLMesh::GlobalInit();
    CloudTile::GlobalInit();CloudManager::GlobalInit();vObject::GlobalInit();
    TileManager2Base::GlobalInit();vStar::GlobalInit();OGLParticleStream::GlobalInit();
    vVessel::GlobalInit();OGLPad::GlobalInit();RingManager::GlobalInit();
    mOverlayShader=Renderer::GetShader("Overlay");mUntexturedShader=Renderer::GetShader("Untextured");
    mResources=true;
    std::clog<<"Native OpenGL renderer: "<<glGetString(GL_RENDERER)<<'\n';
}
RenderInput OGLClient::Poll()
{
    glfwPollEvents();RenderInput input;
    input.close=glfwWindowShouldClose(nativeWindow) || glfwGetKey(nativeWindow,GLFW_KEY_ESCAPE)==GLFW_PRESS;
    glfwGetFramebufferSize(nativeWindow,&input.width,&input.height);
    double x,y;glfwGetCursorPos(nativeWindow,&x,&y);
    bool down=glfwGetMouseButton(nativeWindow,GLFW_MOUSE_BUTTON_RIGHT)==GLFW_PRESS;
    if(down && dragging) {input.yaw=(x-lastX)*-0.005;input.pitch=(y-lastY)*-0.005;}
    dragging=down;lastX=x;lastY=y;input.zoom=scroll;scroll=0;
    return input;
}
void OGLClient::Resize(int width,int height) {clbkSetViewportSize(width,height);}
void OGLClient::clbkMakeContextCurrent(bool current) {glfwMakeContextCurrent(current?nativeWindow:nullptr);}
bool OGLClient::clbkDisplayFrame()
{Evidence::Frame();glfwSwapBuffers(nativeWindow);Evidence::Presented();return true;}
void OGLClient::clbkDestroyRenderWindow(bool)
{
    if(!nativeWindow) return;
    glfwMakeContextCurrent(nativeWindow);mScene.reset();mMeshManager.reset();
    if(mResources) {
        OGLPad::GlobalExit();vVessel::GlobalExit();OGLParticleStream::GlobalExit();vStar::GlobalExit();
        TileManager2Base::GlobalExit();TileManager::GlobalExit();vObject::GlobalExit();mResources=false;
    }
    mTextureManager.reset();Renderer::GlobalExit();
    glfwDestroyWindow(nativeWindow);nativeWindow=nullptr;Evidence::End(true);glfwTerminate();
}
bool RendererResolveFilePath(const std::string& input,std::string& resolved)
{
    std::string name=input;for(char& c:name)if(c=='\\')c='/';
    const auto& context=GetNativeRenderContext();
    for(const auto* root:{context.programFiles,context.highTextures,context.textures,context.planetTextures}) {
        if(!root) continue;
        std::string relative=name;
        if(std::filesystem::path(name).is_absolute()) {
            const auto candidate=std::filesystem::path(name).lexically_normal();
            relative=candidate.lexically_relative(root->Root()).generic_string();
            if(relative.empty() || relative.rfind("..",0)==0) continue;
        }
        if(root->Contains(relative)) {resolved=root->Resolve(relative).string();return true;}
        if(root->ContainsDirectory(relative)) {resolved=root->ResolveDirectory(relative).string();return true;}
    }
    return false;
}
std::string RendererFilePath(const std::string& name)
{
    std::string resolved;if(RendererResolveFilePath(name,resolved))return resolved;
    throw std::runtime_error("Required native renderer asset is missing: "+name);
}
FILE* RendererOpenFile(const char* name,const char* mode)
{
    std::string path;
    return RendererResolveFilePath(name,path)?std::fopen(path.c_str(),mode):nullptr;
}
namespace {
int ORBITER_NATIVE_CALL initialize(const OrbiterNativeHost*,void** instance,char* error,uint32_t capacity) noexcept
{
    try {
        require(g_client==nullptr,"A native OpenGL client already exists");
        auto client=std::make_unique<OGLClient>(nullptr);g_client=client.get();*instance=static_cast<NativeGraphics*>(client.release());return 0;
    } catch(const std::exception& e) {if(capacity)std::snprintf(error,capacity,"%s",e.what());return 1;}
}
void ORBITER_NATIVE_CALL shutdown(void* instance) noexcept
{
    auto* client=static_cast<OGLClient*>(static_cast<NativeGraphics*>(instance));
    try {client->Close();}catch(const std::exception& e){std::cerr<<"OpenGL shutdown failed: "<<e.what()<<'\n';}
    delete client;g_client=nullptr;
}
const OrbiterNativeModuleDescriptor descriptor{sizeof(descriptor),ORBITER_NATIVE_BOOTSTRAP_VERSION,sizeof(void*),
    ORBITER_NATIVE_GRAPHICS,"Production OpenGL client / GLFW",ORBITER_NATIVE_SDK_BUILD,ORBITER_NATIVE_CPP_ABI,initialize,shutdown};
}
extern "C" ORBITER_NATIVE_EXPORT const OrbiterNativeModuleDescriptor* ORBITER_NATIVE_CALL OrbiterNativeQuery(uint32_t version) noexcept
{return version==ORBITER_NATIVE_BOOTSTRAP_VERSION?&descriptor:nullptr;}
