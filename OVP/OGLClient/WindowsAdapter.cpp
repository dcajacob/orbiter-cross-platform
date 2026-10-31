// Copyright (c) Orbiter contributors. Licensed under the MIT License.
// Win32/WGL ownership and the unchanged Windows GraphicsClient interface.
#define ORBITER_MODULE
#include "glad.h"
#include "OGLClient.h"
#include "Scene.h"
#include "Evidence.h"
#include "OGLCamera.h"
#include "Renderer.h"
#include "TileMgr.h"
#include "tilemgr2.h"
#include "HazeMgr.h"
#include "SurfMgr.h"
#include "surfmgr2.h"
#include "VBase.h"
#include "OGLMesh.h"
#include "CloudMgr.h"
#include "cloudmgr2.h"
#include "VStar.h"
#include "Particle.h"
#include "VVessel.h"
#include "OGLPad.h"
#include "RingMgr.h"
#include "imgui.h"
#include "imgui_impl_opengl3.h"
#include <stdexcept>
#include <vector>

namespace {
void require(bool ok,const char *message) { if(!ok) throw std::runtime_error(message); }
using CreateContext = HGLRC(WINAPI *)(HDC,HGLRC,const int *);
}

HWND OGLClient::clbkCreateRenderWindow() {
    try {
        auto video=GetVideoData();video->fullscreen=false;video->winw=1280;video->winh=720;
        hRenderWnd=GraphicsClient::clbkCreateRenderWindow();require(hRenderWnd!=nullptr,"OpenGL render window creation failed");
        SetWindowLongPtr(hRenderWnd,GWL_STYLE,WS_OVERLAPPEDWINDOW|WS_VISIBLE);
        RECT rect{0,0,int(m_width),int(m_height)};AdjustWindowRect(&rect,WS_OVERLAPPEDWINDOW,FALSE);
        SetWindowPos(hRenderWnd,nullptr,0,0,rect.right-rect.left,rect.bottom-rect.top,SWP_NOMOVE|SWP_NOZORDER|SWP_FRAMECHANGED);
        mDC=GetDC(hRenderWnd);require(mDC!=nullptr,"OpenGL window DC failed");
        PIXELFORMATDESCRIPTOR format{};format.nSize=sizeof(format);format.nVersion=1;
        format.dwFlags=PFD_DRAW_TO_WINDOW|PFD_SUPPORT_OPENGL|PFD_DOUBLEBUFFER;
        format.iPixelType=PFD_TYPE_RGBA;format.cColorBits=32;format.cDepthBits=24;format.cStencilBits=8;
        int index=ChoosePixelFormat(mDC,&format);require(index&&SetPixelFormat(mDC,index,&format),"WGL pixel format failed");
        HGLRC bootstrap=wglCreateContext(mDC);require(bootstrap&&wglMakeCurrent(mDC,bootstrap),"WGL bootstrap context failed");
        auto create=reinterpret_cast<CreateContext>(wglGetProcAddress("wglCreateContextAttribsARB"));
        require(create!=nullptr,"WGL_ARB_create_context is unavailable");
        const int attrs[]={0x2091,3,0x2092,3,0x9126,1,0};
        mContext=create(mDC,nullptr,attrs);require(mContext!=nullptr,"WGL 3.3 core context failed");
        wglMakeCurrent(nullptr,nullptr);wglDeleteContext(bootstrap);
        require(wglMakeCurrent(mDC,mContext)&&gladLoadGL(),"OpenGL entry point loading failed");
        Evidence::Begin();
        Renderer::GlobalInit(m_width,m_height);
        mTextureManager=std::make_unique<TextureManager>();
        mMeshManager=std::make_unique<OGLMeshManager>();
        mScene=std::make_unique<Scene>(m_width,m_height);
        TileManager::GlobalInit();HazeManager::GlobalInit();SurfTile::GlobalInit();
        SurfaceManager::GlobalInit();vBase::GlobalInit();OGLMesh::GlobalInit();
        CloudTile::GlobalInit();CloudManager::GlobalInit();vObject::GlobalInit();
        TileManager2Base::GlobalInit();vStar::GlobalInit();OGLParticleStream::GlobalInit();
        vVessel::GlobalInit();OGLPad::GlobalInit();RingManager::GlobalInit();
        mOverlayShader=Renderer::GetShader("Overlay");mUntexturedShader=Renderer::GetShader("Untextured");
        mResources=true;
        oapiWriteLog(const_cast<char *>(reinterpret_cast<const char *>(glGetString(GL_RENDERER))));
        return hRenderWnd;
    } catch(const std::exception &e) {
        oapiWriteLog(const_cast<char *>(e.what()));clbkDestroyRenderWindow(false);return nullptr;
    }
}

void OGLClient::clbkMakeContextCurrent(bool current) { wglMakeCurrent(current?mDC:nullptr,current?mContext:nullptr); }
void OGLClient::clbkDestroyRenderWindow(bool fastclose) {
    if(mContext) wglMakeCurrent(mDC,mContext);
    mScene.reset();mMeshManager.reset();
    if(mResources) {
        OGLPad::GlobalExit();vVessel::GlobalExit();OGLParticleStream::GlobalExit();vStar::GlobalExit();
        TileManager2Base::GlobalExit();TileManager::GlobalExit();vObject::GlobalExit();
        mResources=false;
    }
    mTextureManager.reset();Renderer::GlobalExit();
    GraphicsClient::clbkDestroyRenderWindow(fastclose);
    if(mContext){wglMakeCurrent(nullptr,nullptr);wglDeleteContext(mContext);mContext=nullptr;}
    if(mDC){ReleaseDC(hRenderWnd,mDC);mDC=nullptr;}
    hRenderWnd=nullptr;
}
bool OGLClient::clbkDisplayFrame() { return mDC && SwapBuffers(mDC); }
LRESULT OGLClient::RenderWndProc(HWND window,UINT message,WPARAM wp,LPARAM lp) {
    if(message==WM_SIZE && mContext && LOWORD(lp) && HIWORD(lp)) clbkSetViewportSize(LOWORD(lp),HIWORD(lp));
    return GraphicsClient::RenderWndProc(window,message,wp,lp);
}
void OGLClient::clbkImGuiInit() { require(ImGui_ImplOpenGL3_Init("#version 330 core"),"ImGui OpenGL initialization failed"); }
void OGLClient::clbkImGuiShutdown() { ImGui_ImplOpenGL3_Shutdown(); }
void OGLClient::clbkImGuiNewFrame() { ImGui_ImplOpenGL3_NewFrame(); }
void OGLClient::clbkImGuiRenderDrawData() { ImGui_ImplOpenGL3_RenderDrawData(ImGui::GetDrawData()); }
uint64_t OGLClient::clbkImGuiSurfaceTexture(SURFHANDLE surface) { return surface?static_cast<OGLTexture *>(surface)->m_TexId:0; }
SURFHANDLE OGLClient::clbkLoadSurface(const char *name,DWORD flags,bool path) {
    // Direct paths are accepted by the texture reader before Orbiter search paths.
    return LoadSurface(name,int(flags));
}
SURFHANDLE OGLClient::clbkCreateSurface(HBITMAP bitmap) {
    if(!bitmap)return nullptr;
    BITMAP info{};if(!GetObject(bitmap,sizeof(info),&info))return nullptr;
    BITMAPINFO dib{};dib.bmiHeader.biSize=sizeof(BITMAPINFOHEADER);dib.bmiHeader.biWidth=info.bmWidth;
    dib.bmiHeader.biHeight=-info.bmHeight;dib.bmiHeader.biPlanes=1;dib.bmiHeader.biBitCount=32;dib.bmiHeader.biCompression=BI_RGB;
    std::vector<unsigned char> pixels(size_t(info.bmWidth)*info.bmHeight*4);
    HDC dc=CreateCompatibleDC(nullptr);int lines=GetDIBits(dc,bitmap,0,info.bmHeight,pixels.data(),&dib,DIB_RGB_COLORS);DeleteDC(dc);
    if(lines!=info.bmHeight)return nullptr;
    for(size_t i=0;i<pixels.size();i+=4){std::swap(pixels[i],pixels[i+2]);pixels[i+3]=255;}
    auto surface=CreateSurfaceEx(info.bmWidth,info.bmHeight,OAPISURFACE_TEXTURE);
    if(surface && !clbkUpdateSurface(surface,0,0,info.bmWidth,info.bmHeight,pixels.data())){clbkReleaseSurface(surface);return nullptr;}
    return surface;
}
