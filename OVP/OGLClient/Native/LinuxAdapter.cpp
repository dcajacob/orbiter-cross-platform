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
#include "Production/FlightKeys.h"
#include <algorithm>
#include <cmath>
#include <map>
#include <GLFW/glfw3.h>
#include <filesystem>
#include <fstream>
#include <cstdio>
#include <cstring>
#include <iostream>
#include <memory>
#include <stdexcept>
namespace {
void require(bool valid,const char* text) {if(!valid) throw std::runtime_error(text);}
double scroll=0,lastX=0,lastY=0;bool dragging=false;
const std::map<int,unsigned> keyCodes={
    {GLFW_KEY_A,OAPI_KEY_A},
    {GLFW_KEY_B,OAPI_KEY_B},
    {GLFW_KEY_C,OAPI_KEY_C},
    {GLFW_KEY_D,OAPI_KEY_D},
    {GLFW_KEY_E,OAPI_KEY_E},
    {GLFW_KEY_F,OAPI_KEY_F},
    {GLFW_KEY_G,OAPI_KEY_G},
    {GLFW_KEY_H,OAPI_KEY_H},
    {GLFW_KEY_I,OAPI_KEY_I},
    {GLFW_KEY_J,OAPI_KEY_J},
    {GLFW_KEY_K,OAPI_KEY_K},
    {GLFW_KEY_L,OAPI_KEY_L},
    {GLFW_KEY_M,OAPI_KEY_M},
    {GLFW_KEY_N,OAPI_KEY_N},
    {GLFW_KEY_O,OAPI_KEY_O},
    {GLFW_KEY_P,OAPI_KEY_P},
    {GLFW_KEY_Q,OAPI_KEY_Q},
    {GLFW_KEY_R,OAPI_KEY_R},
    {GLFW_KEY_S,OAPI_KEY_S},
    {GLFW_KEY_T,OAPI_KEY_T},
    {GLFW_KEY_U,OAPI_KEY_U},
    {GLFW_KEY_V,OAPI_KEY_V},
    {GLFW_KEY_W,OAPI_KEY_W},
    {GLFW_KEY_X,OAPI_KEY_X},
    {GLFW_KEY_Y,OAPI_KEY_Y},
    {GLFW_KEY_Z,OAPI_KEY_Z},
    {GLFW_KEY_0,OAPI_KEY_0},
    {GLFW_KEY_1,OAPI_KEY_1},
    {GLFW_KEY_2,OAPI_KEY_2},
    {GLFW_KEY_3,OAPI_KEY_3},
    {GLFW_KEY_4,OAPI_KEY_4},
    {GLFW_KEY_5,OAPI_KEY_5},
    {GLFW_KEY_6,OAPI_KEY_6},
    {GLFW_KEY_7,OAPI_KEY_7},
    {GLFW_KEY_8,OAPI_KEY_8},
    {GLFW_KEY_9,OAPI_KEY_9},
    {GLFW_KEY_F1,OAPI_KEY_F1},
    {GLFW_KEY_F2,OAPI_KEY_F2},
    {GLFW_KEY_F3,OAPI_KEY_F3},
    {GLFW_KEY_F4,OAPI_KEY_F4},
    {GLFW_KEY_F5,OAPI_KEY_F5},
    {GLFW_KEY_F6,OAPI_KEY_F6},
    {GLFW_KEY_F7,OAPI_KEY_F7},
    {GLFW_KEY_F8,OAPI_KEY_F8},
    {GLFW_KEY_F9,OAPI_KEY_F9},
    {GLFW_KEY_F10,OAPI_KEY_F10},
    {GLFW_KEY_F11,OAPI_KEY_F11},
    {GLFW_KEY_F12,OAPI_KEY_F12},
    {GLFW_KEY_KP_0,OAPI_KEY_NUMPAD0},
    {GLFW_KEY_KP_1,OAPI_KEY_NUMPAD1},
    {GLFW_KEY_KP_2,OAPI_KEY_NUMPAD2},
    {GLFW_KEY_KP_3,OAPI_KEY_NUMPAD3},
    {GLFW_KEY_KP_4,OAPI_KEY_NUMPAD4},
    {GLFW_KEY_KP_5,OAPI_KEY_NUMPAD5},
    {GLFW_KEY_KP_6,OAPI_KEY_NUMPAD6},
    {GLFW_KEY_KP_7,OAPI_KEY_NUMPAD7},
    {GLFW_KEY_KP_8,OAPI_KEY_NUMPAD8},
    {GLFW_KEY_KP_9,OAPI_KEY_NUMPAD9},
    {GLFW_KEY_LEFT_SHIFT,OAPI_KEY_LSHIFT},
    {GLFW_KEY_RIGHT_SHIFT,OAPI_KEY_RSHIFT},
    {GLFW_KEY_LEFT_CONTROL,OAPI_KEY_LCONTROL},
    {GLFW_KEY_RIGHT_CONTROL,OAPI_KEY_RCONTROL},
    {GLFW_KEY_LEFT_ALT,OAPI_KEY_LALT},
    {GLFW_KEY_RIGHT_ALT,OAPI_KEY_RALT},
    {GLFW_KEY_SPACE,OAPI_KEY_SPACE},
    {GLFW_KEY_APOSTROPHE,OAPI_KEY_APOSTROPHE},
    {GLFW_KEY_SEMICOLON,OAPI_KEY_SEMICOLON},
    {GLFW_KEY_COMMA,OAPI_KEY_COMMA},
    {GLFW_KEY_PERIOD,OAPI_KEY_PERIOD},
    {GLFW_KEY_SLASH,OAPI_KEY_SLASH},
    {GLFW_KEY_MINUS,OAPI_KEY_MINUS},
    {GLFW_KEY_EQUAL,OAPI_KEY_EQUALS},
    {GLFW_KEY_LEFT_BRACKET,OAPI_KEY_LBRACKET},
    {GLFW_KEY_RIGHT_BRACKET,OAPI_KEY_RBRACKET},
    {GLFW_KEY_ENTER,OAPI_KEY_RETURN},
    {GLFW_KEY_BACKSPACE,OAPI_KEY_BACK},
    {GLFW_KEY_TAB,OAPI_KEY_TAB},
    {GLFW_KEY_LEFT,OAPI_KEY_LEFT},
    {GLFW_KEY_RIGHT,OAPI_KEY_RIGHT},
    {GLFW_KEY_UP,OAPI_KEY_UP},
    {GLFW_KEY_DOWN,OAPI_KEY_DOWN},
    {GLFW_KEY_HOME,OAPI_KEY_HOME},
    {GLFW_KEY_END,OAPI_KEY_END},
    {GLFW_KEY_PAGE_UP,OAPI_KEY_PRIOR},
    {GLFW_KEY_PAGE_DOWN,OAPI_KEY_NEXT},
    {GLFW_KEY_INSERT,OAPI_KEY_INSERT},
    {GLFW_KEY_DELETE,OAPI_KEY_DELETE},
    {GLFW_KEY_KP_ADD,OAPI_KEY_ADD},
    {GLFW_KEY_KP_SUBTRACT,OAPI_KEY_SUBTRACT},
    {GLFW_KEY_KP_MULTIPLY,OAPI_KEY_MULTIPLY},
    {GLFW_KEY_KP_DIVIDE,OAPI_KEY_DIVIDE},
    {GLFW_KEY_KP_DECIMAL,OAPI_KEY_DECIMAL},
    {GLFW_KEY_KP_ENTER,OAPI_KEY_NUMPADENTER}};
std::vector<FlightKeyEvent> keyEvents;
int joystickDevice=-1;float initialThrottle=0,lastThrottle=0;bool armed=false,throttleSeen=false;

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
    scroll=0;dragging=false;keyEvents.clear();joystickDevice=-1;armed=false;throttleSeen=false;
    glfwSetKeyCallback(nativeWindow,[](GLFWwindow*,int key,int,int action,int) {
        if(action==GLFW_REPEAT)return;
        auto found=keyCodes.find(key);if(found!=keyCodes.end())keyEvents.push_back({found->second,action==GLFW_PRESS});
    });
    glfwSetScrollCallback(nativeWindow,[](GLFWwindow*,double,double y) {scroll+=y;});
    int width,height;glfwGetFramebufferSize(nativeWindow,&width,&height);m_width=width;m_height=height;
    Evidence::Begin();
    if(!GetNativeRenderContext().evidence.empty()) {
        std::ofstream record(GetNativeRenderContext().evidence/"native-window.json");record.exceptions(std::ios::badbit|std::ios::failbit);
        record<<"{\"backend\":\""<<(glfwGetPlatform()==GLFW_PLATFORM_X11?"x11":"wayland")<<"\"}\n";
    }
    Renderer::GlobalInit(m_width,m_height);
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
    if(glfwGetWindowAttrib(nativeWindow,GLFW_FOCUSED)) {
        for(auto pair:keyCodes)if(glfwGetKey(nativeWindow,pair.first)==GLFW_PRESS)input.flight.keys[pair.second]=char(0x80);
        input.flight.events.swap(keyEvents);
        auto& device=joystickDevice;
        int selected=-1;for(int j=GLFW_JOYSTICK_1;j<=GLFW_JOYSTICK_LAST;++j)if(glfwJoystickPresent(j)){selected=j;break;}
        if(selected!=device){device=selected;armed=false;throttleSeen=false;initialThrottle=lastThrottle=0;}
        if(device>=0) {
            int count=0,buttonsCount=0;const float* axes=glfwGetJoystickAxes(device,&count);const auto* buttons=glfwGetJoystickButtons(device,&buttonsCount);
            auto axis=[&](int i){float v=i<count?axes[i]:0;return std::abs(v)<.05f?0:int(std::lround(std::clamp(v,-1.f,1.f)*1000));};
            input.flight.x=axis(0);input.flight.y=axis(1);input.flight.rz=axis(GetNativeRenderContext().joystickTwistAxis);
            input.flight.alternate=buttonsCount>2 && buttons[2]==GLFW_PRESS;
            const int throttleAxis=GetNativeRenderContext().joystickThrottleAxis;
            if(throttleAxis>=0 && count>throttleAxis) {
                if(!armed){if(!throttleSeen){initialThrottle=axes[throttleAxis];lastThrottle=axes[throttleAxis];throttleSeen=true;}if(std::abs(axes[throttleAxis]-initialThrottle)>.08f)armed=true;}
                if(armed && std::abs(axes[throttleAxis]-lastThrottle)>.001f){input.flight.throttle=std::clamp((1.-axes[throttleAxis])*.5,0.,1.);lastThrottle=axes[throttleAxis];}
            }
        }
    } else keyEvents.clear();
    double x,y;glfwGetCursorPos(nativeWindow,&x,&y);
    bool down=glfwGetMouseButton(nativeWindow,GLFW_MOUSE_BUTTON_RIGHT)==GLFW_PRESS;
    if(down && dragging) {input.yaw=(x-lastX)*-0.005;input.pitch=(y-lastY)*-0.005;}
    dragging=down;lastX=x;lastY=y;input.zoom=scroll;scroll=0;
    return input;
}
void OGLClient::Status(const std::string& text) {glfwSetWindowTitle(nativeWindow,text.c_str());}
void OGLClient::Resize(int width,int height) {clbkSetViewportSize(width,height);}
void OGLClient::clbkMakeContextCurrent(bool current) {glfwMakeContextCurrent(current?nativeWindow:nullptr);}
bool OGLClient::clbkDisplayFrame()
{Evidence::Frame();glfwSwapBuffers(nativeWindow);Evidence::Presented();return true;}
void OGLClient::clbkDestroyRenderWindow(bool)
{
    if(!nativeWindow) return;
    glfwMakeContextCurrent(nativeWindow);mScene.reset();mMeshManager.reset();
    if(mResources) {
        OGLPad::GlobalExit();vVessel::GlobalExit();OGLParticleStream::GlobalExit();vStar::GlobalExit();HazeManager::GlobalExit();
        TileManager2Base::GlobalExit();TileManager::GlobalExit();vObject::GlobalExit();mResources=false;
    }
    ReleaseOverlayBuffers();mTextureManager.reset();Renderer::GlobalExit();
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

int OGLClient::DesktopHeight() const {
    auto* monitor=glfwGetPrimaryMonitor();
    const auto* mode=monitor?glfwGetVideoMode(monitor):nullptr;
    require(mode && mode->height>0,"Native primary display mode unavailable");return mode->height;
}

oapi::SdkPoint OGLClient::CursorPosition() const {
    require(nativeWindow!=nullptr,"Native cockpit cursor requires an open render window");
    double x,y;glfwGetCursorPos(nativeWindow,&x,&y);
    int width,height,fbWidth,fbHeight;glfwGetWindowSize(nativeWindow,&width,&height);glfwGetFramebufferSize(nativeWindow,&fbWidth,&fbHeight);
    require(width>0 && height>0,"Native cockpit cursor requires positive window dimensions");
    return {std::int32_t(x*fbWidth/width),std::int32_t(y*fbHeight/height)};
}
