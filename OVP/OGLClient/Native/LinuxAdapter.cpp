// Licensed under the MIT License
#include "glad.h"
#include "OrbiterNativeBuild.h"
#if ORBITER_BUILD_NATIVE_COCKPIT
#include "imgui.h"
#include "imgui_impl_glfw.h"
#include "imgui_impl_opengl3.h"
#include "Production/NativeCockpitUi.h"
#endif
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
#include "Production/NativeJoystick.h"
#include "Config.h"
#include <algorithm>
#include <cmath>
#include <chrono>
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
std::vector<RenderMouseEvent> mouseEvents;
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
bool guiInitialized=false;
bool glfwInitialized=false;
orbiter::production::NativeJoystickState cockpitJoystick;
int joystickDevice=-1;float initialThrottle=0,lastThrottle=0;bool armed=false,throttleSeen=false;
int engineeringWindowScale=1;
int requestedWindowWidth=1280,requestedWindowHeight=720;
std::ofstream frameTimes;
std::chrono::steady_clock::time_point frameStart;
unsigned timingFrame=0;

void recordWindowGeometry(GLFWwindow* window) {
    const auto& evidence=GetNativeRenderContext().evidence;
    if(evidence.empty())return;
    int width=0,height=0,logicalWidth=0,logicalHeight=0;float scaleX=0,scaleY=0;
    glfwGetFramebufferSize(window,&width,&height);glfwGetWindowSize(window,&logicalWidth,&logicalHeight);
    glfwGetWindowContentScale(window,&scaleX,&scaleY);
    const auto temporary=evidence/"native-window.json.tmp";
    {
        std::ofstream record(temporary);record.exceptions(std::ios::badbit|std::ios::failbit);
        record<<"{\"backend\":\""<<(glfwGetPlatform()==GLFW_PLATFORM_X11?"x11":"wayland")
            <<"\",\"logical_width\":"<<logicalWidth<<",\"logical_height\":"<<logicalHeight
            <<",\"framebuffer_width\":"<<width<<",\"framebuffer_height\":"<<height
            <<",\"content_scale_x\":"<<scaleX<<",\"content_scale_y\":"<<scaleY
            <<",\"requested_width\":"<<requestedWindowWidth<<",\"requested_height\":"<<requestedWindowHeight
            <<",\"engineering_scale\":"<<engineeringWindowScale<<"}\n";
    }
    std::filesystem::rename(temporary,evidence/"native-window.json");
}

void error(int,const char* text) {std::cerr<<"GLFW: "<<text<<'\n';}
}
void OGLClient::Open()
{
    glfwSetErrorCallback(error);require(glfwInit()==GLFW_TRUE,"GLFW initialization failed");
    glfwInitialized=true;
    glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR,3);glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR,3);
    glfwWindowHint(GLFW_OPENGL_PROFILE,GLFW_OPENGL_CORE_PROFILE);
    // The opt-in engineering fixture retains the accepted 1280x720 physical
    // viewport while exercising real 2x Wayland logical/framebuffer conversion.
    // Normal sessions retain the established window policy.
    const auto scaleMarker=GetNativeRenderContext().evidence/"window-scale.enabled";
    engineeringWindowScale=1;
    requestedWindowWidth=1280;requestedWindowHeight=720;
    auto* configuration=GetNativeRenderContext().configuration;
    require(configuration,"Native window requires production configuration");
    const bool configuredWidth=configuration->GetInt("WindowWidth",requestedWindowWidth);
    const bool configuredHeight=configuration->GetInt("WindowHeight",requestedWindowHeight);
    require(requestedWindowWidth>=320 && requestedWindowWidth<=16384 && requestedWindowHeight>=200 && requestedWindowHeight<=16384,
        "Native window dimensions are outside the supported range");
    if(!GetNativeRenderContext().evidence.empty() && std::filesystem::is_regular_file(scaleMarker)) {
        std::ifstream marker(scaleMarker);marker>>engineeringWindowScale;
        require(marker && engineeringWindowScale==2,"Engineering window scale must be 2");
        require(requestedWindowWidth==1280 && requestedWindowHeight==720,"Engineering scale fixture requires the accepted 1280x720 viewport");
    }
    const bool scaledWindow=glfwGetPlatform()==GLFW_PLATFORM_WAYLAND && (configuredWidth || configuredHeight);
    float scaleX=1,scaleY=1;
    if(scaledWindow) {
        auto* monitor=glfwGetPrimaryMonitor();require(monitor,"Configured native window requires a primary display");
        glfwGetMonitorContentScale(monitor,&scaleX,&scaleY);
        require(std::isfinite(scaleX) && std::isfinite(scaleY) && scaleX>=1 && scaleY>=1,"Native display scale is invalid");
    }
    if(engineeringWindowScale==2)scaleX=scaleY=2;
    glfwWindowHint(GLFW_SCALE_FRAMEBUFFER,scaledWindow || engineeringWindowScale==2?GLFW_TRUE:GLFW_FALSE);
    nativeWindow=glfwCreateWindow(int(std::lround(requestedWindowWidth/scaleX)),int(std::lround(requestedWindowHeight/scaleY)),"Orbiter: native production engine / Sol / ShuttlePB",nullptr,nullptr);
    require(nativeWindow!=nullptr,"Native OpenGL window creation failed");
    glfwMakeContextCurrent(nativeWindow);glfwSwapInterval(1);
    require(gladLoadGLLoader(reinterpret_cast<GLADloadproc>(glfwGetProcAddress))!=0,"Native OpenGL function loading failed");
    if(scaledWindow || engineeringWindowScale==2) {
        // Wayland announces the entered output's scale after the first buffer
        // commit. Settle it before constructing the original fixed-size Pane.
        const auto deadline=std::chrono::steady_clock::now()+std::chrono::seconds(5);
        int width=0,height=0;unsigned primingPresents=0;
        for(;;) {
            glfwGetFramebufferSize(nativeWindow,&width,&height);
            if(width==requestedWindowWidth && height==requestedWindowHeight)break;
            require(std::chrono::steady_clock::now()<deadline,engineeringWindowScale==2?
                "Engineering window did not enter a 2x output":"Configured native framebuffer dimensions are unavailable");
            if(scaledWindow && engineeringWindowScale!=2 && primingPresents) {
                // Fractional-scale feedback can differ from the output's
                // integer scale. Use the entered surface's actual content scale.
                glfwGetWindowContentScale(nativeWindow,&scaleX,&scaleY);
                require(std::isfinite(scaleX) && std::isfinite(scaleY) && scaleX>=1 && scaleY>=1,"Native window scale is invalid");
                int logicalWidth=0,logicalHeight=0;glfwGetWindowSize(nativeWindow,&logicalWidth,&logicalHeight);
                const int desiredWidth=int(std::lround(requestedWindowWidth/scaleX));
                const int desiredHeight=int(std::lround(requestedWindowHeight/scaleY));
                if(logicalWidth!=desiredWidth || logicalHeight!=desiredHeight)glfwSetWindowSize(nativeWindow,desiredWidth,desiredHeight);
            }
            glClear(GL_COLOR_BUFFER_BIT);glfwSwapBuffers(nativeWindow);++primingPresents;glfwPollEvents();
        }
        if(!GetNativeRenderContext().evidence.empty()) {
            std::ofstream priming(GetNativeRenderContext().evidence/(engineeringWindowScale==2?"engineering-window-priming.json":"window-priming.json"));
            priming<<"{\"blank_presents_before_engine_scene\":"<<primingPresents<<"}\n";
        }
    }
    cockpitJoystick.Reset();
#if ORBITER_BUILD_NATIVE_COCKPIT
    glfwSetJoystickCallback([](int device, int) {
        // GLFW can reuse the same slot for a new connection between two polls.
        cockpitJoystick.DeviceChanged(device);
    });
#endif
    scroll=0;dragging=false;keyEvents.clear();mouseEvents.clear();joystickDevice=-1;armed=false;throttleSeen=false;
    glfwSetKeyCallback(nativeWindow,[](GLFWwindow*,int key,int,int action,int) {
        if(action==GLFW_REPEAT)return;
        auto found=keyCodes.find(key);if(found!=keyCodes.end())keyEvents.push_back({found->second,action==GLFW_PRESS});
    });
    glfwSetMouseButtonCallback(nativeWindow,[](GLFWwindow*,int button,int action,int) {
        if(button!=GLFW_MOUSE_BUTTON_LEFT && button!=GLFW_MOUSE_BUTTON_RIGHT)return;
        const auto point=g_client->CursorPosition();
        const auto event=button==GLFW_MOUSE_BUTTON_LEFT?
            (action==GLFW_PRESS?RenderMouseAction::LeftDown:RenderMouseAction::LeftUp):
            (action==GLFW_PRESS?RenderMouseAction::RightDown:RenderMouseAction::RightUp);
        mouseEvents.push_back({event,point.x,point.y,0});
    });
    glfwSetScrollCallback(nativeWindow,[](GLFWwindow*,double,double y) {
        scroll+=y;const auto point=g_client->CursorPosition();mouseEvents.push_back({RenderMouseAction::Wheel,point.x,point.y,y});
    });
    int width,height;glfwGetFramebufferSize(nativeWindow,&width,&height);m_width=width;m_height=height;
    Evidence::Begin();
    recordWindowGeometry(nativeWindow);
    if(!GetNativeRenderContext().evidence.empty()) {
        const auto& visual=configuration->CfgVisualPrm;
        const auto& planet=configuration->CfgPRenderPrm;
        std::ofstream settings(GetNativeRenderContext().evidence/"native-render-settings.json");
        settings.exceptions(std::ios::badbit|std::ios::failbit);
        settings<<"{\"swap_interval\":1,\"planet_max_level\":"<<visual.PlanetMaxLevel
            <<",\"patch_grid_power\":"<<planet.PatchRes<<",\"resolution_bias\":"<<planet.ResolutionBias
            <<",\"clouds\":"<<visual.bClouds<<",\"cloud_shadows\":"<<visual.bCloudShadows
            <<",\"vessel_shadows\":"<<visual.bVesselShadows<<",\"night_lights\":"<<visual.bNightlights
            <<",\"water_reflection\":"<<visual.bWaterreflect<<",\"specular_ripples\":"<<visual.bSpecularRipple
            <<",\"haze\":"<<visual.bHaze<<",\"fog\":"<<visual.bFog<<",\"specular\":"<<visual.bSpecular
            <<",\"particle_streams\":"<<visual.bParticleStreams<<",\"local_lights\":"<<visual.bLocalLight
            <<",\"elevation_mode\":"<<visual.ElevMode<<"}\n";
    }
    if(frameTimes.is_open())frameTimes.close();
    timingFrame=0;
    if(!GetNativeRenderContext().evidence.empty() &&
       std::filesystem::is_regular_file(GetNativeRenderContext().evidence/"frame-times.enabled")) {
        frameTimes.open(GetNativeRenderContext().evidence/"frame-times.csv");
        frameTimes.exceptions(std::ios::badbit|std::ios::failbit);
        frameTimes<<"frame,loop_start_ns,swap_start_ns,present_end_ns,framebuffer_width,framebuffer_height,visible,iconified,focused\n";
    }
    glfwSetFramebufferSizeCallback(nativeWindow,[](GLFWwindow* window,int,int){recordWindowGeometry(window);});
    glfwSetWindowContentScaleCallback(nativeWindow,[](GLFWwindow* window,float,float){recordWindowGeometry(window);});
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
    if(frameTimes.is_open())frameStart=std::chrono::steady_clock::now();
    glfwPollEvents();RenderInput input;
    input.mouse.swap(mouseEvents);
    input.close=glfwWindowShouldClose(nativeWindow);
    bool captureKeyboard=false;
#if ORBITER_BUILD_NATIVE_COCKPIT
    captureKeyboard=CockpitGuiCapturesKeyboard();
#endif
    input.close=input.close || (!captureKeyboard && glfwGetKey(nativeWindow,GLFW_KEY_ESCAPE)==GLFW_PRESS);
    glfwGetFramebufferSize(nativeWindow,&input.width,&input.height);
    if(glfwGetWindowAttrib(nativeWindow,GLFW_FOCUSED) && !captureKeyboard) {
        for(auto pair:keyCodes)if(glfwGetKey(nativeWindow,pair.first)==GLFW_PRESS)input.flight.keys[pair.second]=char(0x80);
        input.flight.events.swap(keyEvents);
#if ORBITER_BUILD_NATIVE_COCKPIT
        auto& render=GetNativeRenderContext();
        const auto& prm=render.configuration->CfgJoystickPrm;
        int device=prm.Joy_idx>0 && prm.Joy_idx<=GLFW_JOYSTICK_LAST+1 ? int(prm.Joy_idx)-1 : -1;
        if(device>=0 && !glfwJoystickPresent(device))device=-1;
        int count=0,buttonsCount=0;
        const auto* buttons=device>=0 ? glfwGetJoystickButtons(device,&buttonsCount) : nullptr;
        const char* guid = buttons ? glfwGetJoystickGUID(device) : nullptr;
        const bool alternate = NativeJoystickAlternate(buttons, buttonsCount, guid ? guid : "");
        const float* axes=device>=0 ? glfwGetJoystickAxes(device,&count) : nullptr;
        cockpitJoystick.Poll(axes ? device : -1,axes,count,render.joystickTwistAxis,
            NativeThrottleAxis(prm.ThrottleAxis,render.joystickThrottleAxis),
            prm.Deadzone,prm.ThrottleSaturation,prm.bThrottleIgnore,input.flight,render.joystickThrottleInverted);
        input.flight.alternate=axes && alternate;
#else
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
#endif
    } else keyEvents.clear();
    double x,y;glfwGetCursorPos(nativeWindow,&x,&y);
    bool down=glfwGetMouseButton(nativeWindow,GLFW_MOUSE_BUTTON_RIGHT)==GLFW_PRESS;
    if(down && dragging) {input.yaw=(x-lastX)*-0.005;input.pitch=(y-lastY)*-0.005;}
    dragging=down;lastX=x;lastY=y;input.zoom=scroll;scroll=0;
    return input;
}
std::vector<NativeJoystickDevice> OGLClient::Joysticks() const {
    std::vector<NativeJoystickDevice> devices;
    for(int id=GLFW_JOYSTICK_1;id<=GLFW_JOYSTICK_LAST;++id)if(glfwJoystickPresent(id)) {
        int count=0;glfwGetJoystickAxes(id,&count);
        const char* name=glfwGetJoystickName(id);
        devices.push_back({unsigned(id+1),name ? name : "Joystick",count});
    }
    return devices;
}
void OGLClient::Status(const std::string& text) {glfwSetWindowTitle(nativeWindow,text.c_str());}
void OGLClient::Resize(int width,int height) {clbkSetViewportSize(width,height);}
void OGLClient::clbkMakeContextCurrent(bool current) {glfwMakeContextCurrent(current?nativeWindow:nullptr);}
bool OGLClient::clbkDisplayFrame()
{
    Evidence::Frame();
    const auto swapStart=frameTimes.is_open()?std::chrono::steady_clock::now():std::chrono::steady_clock::time_point{};
    glfwSwapBuffers(nativeWindow);Evidence::Presented();
    if(frameTimes.is_open()) {
        const auto end=std::chrono::steady_clock::now();
        const auto ns=[](auto t){return std::chrono::duration_cast<std::chrono::nanoseconds>(t.time_since_epoch()).count();};
        int width=0,height=0;glfwGetFramebufferSize(nativeWindow,&width,&height);
        frameTimes<<++timingFrame<<','<<ns(frameStart)<<','<<ns(swapStart)<<','<<ns(end)<<','<<width<<','<<height
            <<','<<glfwGetWindowAttrib(nativeWindow,GLFW_VISIBLE)<<','<<glfwGetWindowAttrib(nativeWindow,GLFW_ICONIFIED)
            <<','<<glfwGetWindowAttrib(nativeWindow,GLFW_FOCUSED)<<'\n';
    }
    return true;
}
void OGLClient::clbkDestroyRenderWindow(bool)
{
    if(!nativeWindow) {
        if(glfwInitialized) {glfwTerminate();glfwInitialized=false;}
        return;
    }
    SetCameraRotation(false);
    glfwMakeContextCurrent(nativeWindow);mScene.reset();mMeshManager.reset();
    if(mResources) {
        OGLPad::GlobalExit();vVessel::GlobalExit();OGLParticleStream::GlobalExit();vStar::GlobalExit();HazeManager::GlobalExit();
        TileManager2Base::GlobalExit();TileManager::GlobalExit();vObject::GlobalExit();mResources=false;
    }
    ReleaseOverlayBuffers();mTextureManager.reset();Renderer::GlobalExit();
    glfwDestroyWindow(nativeWindow);nativeWindow=nullptr;Evidence::End(true);glfwTerminate();glfwInitialized=false;
    if(frameTimes.is_open())frameTimes.close();
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
void OGLClient::SetCursorPosition(oapi::SdkPoint point) {
    require(nativeWindow!=nullptr,"Native camera cursor requires an open render window");
    int width,height,fbWidth,fbHeight;glfwGetWindowSize(nativeWindow,&width,&height);glfwGetFramebufferSize(nativeWindow,&fbWidth,&fbHeight);
    require(width>0 && height>0 && fbWidth>0 && fbHeight>0,"Native camera cursor requires a positive viewport");
    glfwSetCursorPos(nativeWindow,double(point.x)*width/fbWidth,double(point.y)*height/fbHeight);
}
void OGLClient::SetCameraRotation(bool enabled) {
    require(!enabled || nativeWindow,"Camera rotation requires an open render window");
    if(nativeWindow) {
        double x=0,y=0;
        if(enabled)glfwGetCursorPos(nativeWindow,&x,&y);
        glfwSetInputMode(nativeWindow,GLFW_CURSOR,enabled ? GLFW_CURSOR_DISABLED : GLFW_CURSOR_NORMAL);
        if(enabled) {
            // Called by the host after Poll, outside GLFW callbacks. Drain the
            // grab's synthetic enter/center events before restoring its virtual
            // client anchor; XWayland otherwise reports a spurious first delta.
            glfwPollEvents();
            glfwSetCursorPos(nativeWindow,x,y);
        }
    }
    auto& context=GetNativeRenderContext();context.cameraRotating=enabled;
    if(std::filesystem::is_regular_file(context.evidence/"camera-pointer.enabled")) {
        const auto path=context.evidence/"camera-capture.csv";
        const bool header=!std::filesystem::exists(path);
        std::ofstream trace(path,std::ios::app);
        if(header)trace<<"capture,cursor_mode,focused\n";
        trace<<enabled<<','<<(nativeWindow ? glfwGetInputMode(nativeWindow,GLFW_CURSOR) : GLFW_CURSOR_NORMAL)
            <<','<<(nativeWindow ? glfwGetWindowAttrib(nativeWindow,GLFW_FOCUSED) : 0)<<'\n';
    }
}

void OGLClient::InitGui() {
#if ORBITER_BUILD_NATIVE_COCKPIT
    require(ImGui::GetCurrentContext()!=nullptr, "Engine cockpit GUI context missing");
    require(ImGui_ImplGlfw_InitForOpenGL(nativeWindow, true), "GLFW cockpit GUI initialization failed");
    if (!ImGui_ImplOpenGL3_Init("#version 330 core")) {
        ImGui_ImplGlfw_Shutdown();
        throw std::runtime_error("OpenGL cockpit GUI initialization failed");
    }
    guiInitialized=true;
#else
    throw std::runtime_error("This renderer was built without cockpit GUI support");
#endif
}
void OGLClient::NewGuiFrame() {
#if ORBITER_BUILD_NATIVE_COCKPIT
    require(guiInitialized, "Cockpit GUI backend missing");
    ImGui_ImplOpenGL3_NewFrame();
    ImGui_ImplGlfw_NewFrame();
#else
    throw std::runtime_error("This renderer was built without cockpit GUI support");
#endif
}
void OGLClient::RenderGui() {
#if ORBITER_BUILD_NATIVE_COCKPIT
    require(guiInitialized, "Cockpit GUI backend missing");
    ImGui::Render();
    ImGui_ImplOpenGL3_RenderDrawData(ImGui::GetDrawData());
#else
    throw std::runtime_error("This renderer was built without cockpit GUI support");
#endif
}
void OGLClient::ShutdownGui() {
#if ORBITER_BUILD_NATIVE_COCKPIT
    if (guiInitialized) {
        ImGui_ImplOpenGL3_Shutdown();
        ImGui_ImplGlfw_Shutdown();
        guiInitialized=false;
    }
#endif
}

void OGLClient::ReplayGuiInput(const std::string& event,int x,int y,const std::string& text) {
#if ORBITER_BUILD_NATIVE_COCKPIT
    require(guiInitialized,"Replay requires an initialized cockpit GUI");
    if(event=="move" || event=="left_down" || event=="popup_down" || event=="left_up") {
        glfwSetCursorPos(nativeWindow,x,y);
        ImGui_ImplGlfw_CursorPosCallback(nativeWindow,x,y);
        if(event!="move") ImGui_ImplGlfw_MouseButtonCallback(nativeWindow,GLFW_MOUSE_BUTTON_LEFT,event=="left_up"?GLFW_RELEASE:GLFW_PRESS,0);
    } else if(event=="key_down" || event=="key_up") {
        require(x==13,"UI replay currently supports the declared Enter key");
        ImGui_ImplGlfw_KeyCallback(nativeWindow,GLFW_KEY_ENTER,glfwGetKeyScancode(GLFW_KEY_ENTER),event=="key_down"?GLFW_PRESS:GLFW_RELEASE,0);
    } else if(event=="text") {
        for(unsigned char code:text) {
            require(code>0 && code<128,"UI replay requires declared ASCII text");
            ImGui_ImplGlfw_CharCallback(nativeWindow,code);
        }
    } else throw std::invalid_argument("Unknown GUI replay event");
#else
    throw std::runtime_error("This renderer was built without cockpit GUI support");
#endif
}
