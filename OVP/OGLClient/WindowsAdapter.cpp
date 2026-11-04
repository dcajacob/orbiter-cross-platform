// Copyright (c) Orbiter contributors. Licensed under the MIT License.
// Win32/WGL ownership and the unchanged Windows GraphicsClient interface.
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
#include <fstream>
#include <cstdlib>
#include <vector>

struct WindowsSurfaceDC {
    HDC dc=nullptr;
    HBITMAP bitmap=nullptr;
    HGDIOBJ previous=nullptr;
    void* pixels=nullptr;
    OGLTexture* texture=nullptr;
    ~WindowsSurfaceDC() {
        if(dc && previous)SelectObject(dc,previous);
        if(bitmap)DeleteObject(bitmap);
        if(dc)DeleteDC(dc);
        if(texture)texture->Release();
    }
};
void WindowsSurfaceDCDelete::operator()(WindowsSurfaceDC* lease) const {delete lease;}

namespace {
void require(bool ok,const char *message) { if(!ok) throw std::runtime_error(message); }
void requireGl(const char* message) {require(glGetError()==GL_NO_ERROR,message);}
using CreateContext = HGLRC(WINAPI *)(HDC,HGLRC,const int *);

class WglContextScope {
    HDC previousDC=wglGetCurrentDC();
    HGLRC previousContext=wglGetCurrentContext();
public:
    WglContextScope(HDC dc,HGLRC context) {
        require(dc && context,"GDI surface requires the live client context");
        if(previousDC!=dc || previousContext!=context) {
            if(!wglMakeCurrent(dc,context)) {
                wglMakeCurrent(previousDC,previousContext);
                throw std::runtime_error("GDI surface context acquisition failed");
            }
        }
    }
    ~WglContextScope() {
        if(wglGetCurrentDC()!=previousDC || wglGetCurrentContext()!=previousContext)
            wglMakeCurrent(previousDC,previousContext);
    }
};

class PixelTransferScope {
    GLenum bufferTarget,bufferBinding;
    GLenum parameters[4];
    GLint values[4]{},texture=0,buffer=0;
public:
    explicit PixelTransferScope(bool reading)
        :bufferTarget(reading?GL_PIXEL_PACK_BUFFER:GL_PIXEL_UNPACK_BUFFER),
         bufferBinding(reading?GL_PIXEL_PACK_BUFFER_BINDING:GL_PIXEL_UNPACK_BUFFER_BINDING) {
        const GLenum pack[]={GL_PACK_ALIGNMENT,GL_PACK_ROW_LENGTH,GL_PACK_SKIP_PIXELS,GL_PACK_SKIP_ROWS};
        const GLenum unpack[]={GL_UNPACK_ALIGNMENT,GL_UNPACK_ROW_LENGTH,GL_UNPACK_SKIP_PIXELS,GL_UNPACK_SKIP_ROWS};
        glGetIntegerv(GL_TEXTURE_BINDING_2D,&texture);
        glGetIntegerv(bufferBinding,&buffer);
        glBindBuffer(bufferTarget,0);
        for(unsigned i=0;i<4;++i) {
            parameters[i]=reading?pack[i]:unpack[i];
            glGetIntegerv(parameters[i],&values[i]);
            glPixelStorei(parameters[i],i?0:4);
        }
    }
    ~PixelTransferScope() {
        for(unsigned i=0;i<4;++i)glPixelStorei(parameters[i],values[i]);
        glBindBuffer(bufferTarget,buffer);
        glBindTexture(GL_TEXTURE_2D,texture);
    }
};

void gdiFailure(const char* message) {
    oapiWriteLog(const_cast<char*>(message));
    if(std::ifstream("ogl-evidence.enabled").good())
        std::ofstream("graphics-errors.txt",std::ios::app)<<message<<'\n';
}
}

HWND OGLClient::clbkCreateRenderWindow() {
    try {
        auto video=GetVideoData();video->fullscreen=false;video->winw=1280;video->winh=720;
        hRenderWnd=GraphicsClient::clbkCreateRenderWindow();require(hRenderWnd!=nullptr,"OpenGL render window creation failed");
        SetWindowLongPtr(hRenderWnd,GWLP_USERDATA,reinterpret_cast<LONG_PTR>(this));
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
    // Outstanding GDI leases own real surface references and must end first.
    mSurfaceDCs.clear();
    mScene.reset();mMeshManager.reset();
    if(mResources) {
        OGLPad::GlobalExit();vVessel::GlobalExit();OGLParticleStream::GlobalExit();vStar::GlobalExit();HazeManager::GlobalExit();
        TileManager2Base::GlobalExit();TileManager::GlobalExit();vObject::GlobalExit();
        mResources=false;
    }
    ReleaseOverlayBuffers();mTextureManager.reset();Renderer::GlobalExit();
    GraphicsClient::clbkDestroyRenderWindow(fastclose);
    bool contextDeleted=true;
    if(mContext){wglMakeCurrent(nullptr,nullptr);contextDeleted=wglDeleteContext(mContext)!=FALSE;mContext=nullptr;}
    Evidence::End(contextDeleted);
    if(mDC){ReleaseDC(hRenderWnd,mDC);mDC=nullptr;}
    hRenderWnd=nullptr;
}
bool OGLClient::clbkDisplayFrame() {
    // Read back the complete application frame, after Output2DData and ImGui.
    try { Evidence::Frame(); }
    catch(const std::exception &error) {
        oapiWriteLog(const_cast<char *>(error.what()));
        std::ofstream failure("graphics-failure.txt");failure<<error.what()<<'\n';failure.close();
        // Evidence capture is test-only; its failure must remain a nonzero run.
        std::exit(EXIT_FAILURE);
    }
    bool success=mDC && SwapBuffers(mDC);
    if(success)Evidence::Presented();
    else oapiWriteLog(const_cast<char *>("OpenGL frame presentation failed"));
    return success;
}
LRESULT OGLClient::RenderWndProc(HWND window,UINT message,WPARAM wp,LPARAM lp) {
    if(message==WM_GETMINMAXINFO) {
        auto result=GraphicsClient::RenderWndProc(window,message,wp,lp);
        auto limits=reinterpret_cast<MINMAXINFO *>(lp);
        // Hosted desktops may be smaller than the required test viewport.
        // Allow an ordinary window to extend beyond that desktop's bounds.
        limits->ptMaxTrackSize.x=std::max(LONG(1400),limits->ptMaxTrackSize.x);
        limits->ptMaxTrackSize.y=std::max(LONG(900),limits->ptMaxTrackSize.y);
        return result;
    }
    if(message==WM_SIZE && mContext && LOWORD(lp) && HIWORD(lp)) clbkSetViewportSize(LOWORD(lp),HIWORD(lp));
    return GraphicsClient::RenderWndProc(window,message,wp,lp);
}
void OGLClient::clbkImGuiInit() {
    // The production Win32 platform backend owns the main window. Additional
    // WGL window/context callbacks are not part of this external-view gate.
    ImGui::GetIO().ConfigFlags &= ~ImGuiConfigFlags_ViewportsEnable;
    oapiWriteLog(const_cast<char *>("OGLClient: dialogs use the main window; floating WGL platform windows are unsupported"));
    require(ImGui_ImplOpenGL3_Init("#version 330 core"),"ImGui OpenGL initialization failed");
}
void OGLClient::clbkImGuiShutdown() { ImGui_ImplOpenGL3_Shutdown(); }
void OGLClient::clbkImGuiNewFrame() { ImGui_ImplOpenGL3_NewFrame(); }
void OGLClient::clbkImGuiRenderDrawData() {
    ImGui::Render();
    auto data=ImGui::GetDrawData();require(data!=nullptr,"ImGui frame finalization failed");
    ImGui_ImplOpenGL3_RenderDrawData(data);
}
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

HDC OGLClient::clbkGetSurfaceDC(SURFHANDLE surface) {
    if(!surface)return nullptr;
    try {
        WglContextScope context(mDC,mContext);
        require(mSurfaceDCs.find(surface)==mSurfaceDCs.end(),"GDI surface DC is already acquired");
        auto* texture=static_cast<OGLTexture*>(surface);
        require(texture->m_Width>0 && texture->m_Height>0,"Invalid GDI surface dimensions");
        std::unique_ptr<WindowsSurfaceDC,WindowsSurfaceDCDelete> lease(new WindowsSurfaceDC);
        lease->dc=CreateCompatibleDC(mDC);
        require(lease->dc!=nullptr,"GDI surface memory DC creation failed");
        BITMAPINFO info{};
        info.bmiHeader.biSize=sizeof(BITMAPINFOHEADER);
        info.bmiHeader.biWidth=texture->m_Width;
        // Match the existing HBITMAP adapter's top-down BGRA row order.
        info.bmiHeader.biHeight=-texture->m_Height;
        info.bmiHeader.biPlanes=1;
        info.bmiHeader.biBitCount=32;
        info.bmiHeader.biCompression=BI_RGB;
        lease->bitmap=CreateDIBSection(lease->dc,&info,DIB_RGB_COLORS,&lease->pixels,nullptr,0);
        require(lease->bitmap && lease->pixels,"GDI surface DIB creation failed");
        HGDIOBJ previous=SelectObject(lease->dc,lease->bitmap);
        require(previous && previous!=HGDI_ERROR,"GDI surface bitmap selection failed");
        lease->previous=previous;
        {
            PixelTransferScope transfer(true);
            glBindTexture(GL_TEXTURE_2D,texture->m_TexId);
            glGetTexImage(GL_TEXTURE_2D,0,GL_BGRA,GL_UNSIGNED_BYTE,lease->pixels);
            requireGl("GDI surface readback failed");
        }
        texture->AddRef();lease->texture=texture;
        HDC dc=lease->dc;
        mSurfaceDCs.emplace(surface,std::move(lease));
        return dc;
    } catch(const std::exception& error) {
        gdiFailure(error.what());return nullptr;
    }
}

void OGLClient::clbkReleaseSurfaceDC(SURFHANDLE surface,HDC dc) {
    auto found=mSurfaceDCs.find(surface);
    if(found==mSurfaceDCs.end() || found->second->dc!=dc) {
        gdiFailure("GDI surface release does not match its acquired DC");return;
    }
    try {
        WglContextScope context(mDC,mContext);
        auto lease=std::move(found->second);mSurfaceDCs.erase(found);
        // GDI can batch writes to a DIB. Complete them before CPU/GL access.
        require(GdiFlush()!=FALSE,"GDI surface flush failed");
        auto* bytes=static_cast<unsigned char*>(lease->pixels);
        const size_t pixels=size_t(lease->texture->m_Width)*size_t(lease->texture->m_Height);
        // GDI RGB drawing does not supply an alpha channel, as with HBITMAP upload.
        for(size_t i=0;i<pixels;++i)bytes[4*i+3]=255;
        {
            PixelTransferScope transfer(false);
            glBindTexture(GL_TEXTURE_2D,lease->texture->m_TexId);
            glTexSubImage2D(GL_TEXTURE_2D,0,0,0,lease->texture->m_Width,lease->texture->m_Height,
                            GL_BGRA,GL_UNSIGNED_BYTE,bytes);
            requireGl("GDI surface upload failed");
        }
        lease.reset();
    } catch(const std::exception& error) {gdiFailure(error.what());}
}
