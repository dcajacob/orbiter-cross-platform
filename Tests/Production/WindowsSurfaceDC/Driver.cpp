// Licensed under the MIT License
// Real public SDK/GDI/OpenGL calls in the production Windows application.
#define ORBITER_MODULE
#include "Orbitersdk.h"
#include <GL/gl.h>
#include <cstdlib>
#include <cstdio>
#include <fstream>
#include <stdexcept>
#include "WglBitmapTarget.h"

namespace {
void require(bool value,const char* message) {if(!value)throw std::runtime_error(message);}

class CompatibilityContext {
    HDC previousDC=wglGetCurrentDC();
    HGLRC previousContext=wglGetCurrentContext();
    HINSTANCE instance=GetModuleHandleW(nullptr);
    HWND window=nullptr;
    HDC dc=nullptr;
    HGLRC context=nullptr;
    bool registered=false;
    static const wchar_t* Name() {return L"Orbiter.SurfaceDC.ForeignContext";}
    void cleanup() noexcept {
        wglMakeCurrent(previousDC,previousContext);
        if(context)wglDeleteContext(context);
        if(dc && window)ReleaseDC(window,dc);
        if(window)DestroyWindow(window);
        if(registered)UnregisterClassW(Name(),instance);
    }
public:
    CompatibilityContext() {
        try {
            require(previousDC && previousContext,"Actual client context is missing");
            WNDCLASSEXW type{};type.cbSize=sizeof(type);type.style=CS_OWNDC;
            type.lpfnWndProc=DefWindowProcW;type.hInstance=instance;type.lpszClassName=Name();
            registered=RegisterClassExW(&type)!=0;require(registered,"Compatibility window class failed");
            window=CreateWindowExW(WS_EX_TOOLWINDOW|WS_EX_NOACTIVATE,Name(),L"",WS_POPUP,
                                  0,0,16,16,nullptr,nullptr,instance,nullptr);
            require(window!=nullptr,"Compatibility window failed");
            dc=GetDC(window);require(dc!=nullptr,"Compatibility window DC failed");
            PIXELFORMATDESCRIPTOR format{};format.nSize=sizeof(format);format.nVersion=1;
            format.dwFlags=PFD_DRAW_TO_WINDOW|PFD_SUPPORT_OPENGL;
            format.iPixelType=PFD_TYPE_RGBA;format.cColorBits=32;
            const int index=ChoosePixelFormat(dc,&format);
            require(index && SetPixelFormat(dc,index,&format),"Compatibility pixel format failed");
            context=wglCreateContext(dc);require(context!=nullptr,"Compatibility OpenGL context failed");
        } catch(...) {cleanup();throw;}
    }
    void Activate() {require(wglMakeCurrent(dc,context)!=FALSE,"Compatibility context acquisition failed");}
    void Restore() {require(wglMakeCurrent(previousDC,previousContext)!=FALSE,"Actual client context restoration failed");}
    HGLRC Context() const {return context;}
    HDC DC() const {return dc;}
    ~CompatibilityContext() {cleanup();}
};

class PixelState {
    const GLenum keys[8]={GL_PACK_ALIGNMENT,GL_PACK_ROW_LENGTH,GL_PACK_SKIP_PIXELS,GL_PACK_SKIP_ROWS,
                           GL_UNPACK_ALIGNMENT,GL_UNPACK_ROW_LENGTH,GL_UNPACK_SKIP_PIXELS,GL_UNPACK_SKIP_ROWS};
    const GLint selected[8]={8,17,2,1,8,19,3,2};
    GLint previous[8]{};
public:
    PixelState() {for(unsigned i=0;i<8;++i){glGetIntegerv(keys[i],&previous[i]);glPixelStorei(keys[i],selected[i]);}}
    void Check() const {
        for(unsigned i=0;i<8;++i){GLint value=0;glGetIntegerv(keys[i],&value);require(value==selected[i],"GDI bridge changed caller pixel-transfer state");}
    }
    ~PixelState() {for(unsigned i=0;i<8;++i)glPixelStorei(keys[i],previous[i]);}
};

COLORREF color(int x,int y,unsigned repeat) {
    return RGB((x*17+repeat)%256,(y*31+repeat*3)%256,(x+y*13)%256);
}

void roundtrip(unsigned repeat,CompatibilityContext* foreign) {
    const HDC clientDC=wglGetCurrentDC();const HGLRC clientContext=wglGetCurrentContext();
    PixelState state;
    SURFHANDLE surface=oapiCreateSurface(13,7);require(surface!=nullptr,"Actual test surface creation failed");
    if(foreign)foreign->Activate();
    const HDC expectedDC=foreign?foreign->DC():clientDC;
    const HGLRC expectedContext=foreign?foreign->Context():clientContext;
    auto contextCheck=[&] {require(wglGetCurrentDC()==expectedDC && wglGetCurrentContext()==expectedContext,
                                  "GDI bridge did not restore the caller's OpenGL context");};
    HDC dc=oapiGetDC(surface);require(dc!=nullptr,"Client supplied no real GDI surface DC");contextCheck();
    HBITMAP bitmap=CreateCompatibleBitmap(dc,13,7);require(bitmap!=nullptr,"Surface-compatible bitmap failed");
    BITMAP info{};require(GetObject(bitmap,sizeof(info),&info)==sizeof(info) &&
        info.bmWidth==13 && info.bmHeight==7 && info.bmBitsPixel==32,"Actual GDI surface format/dimensions differ");
    HDC memory=CreateCompatibleDC(dc);require(memory!=nullptr,"Surface-compatible memory DC failed");
    HGDIOBJ previous=SelectObject(memory,bitmap);require(previous && previous!=HGDI_ERROR,"Test bitmap selection failed");
    for(int y=0;y<7;++y)for(int x=0;x<13;++x)
        require(SetPixel(memory,x,y,color(x,y,repeat))!=CLR_INVALID,"Actual GDI pixel write failed");
    require(BitBlt(dc,0,0,13,7,memory,0,0,SRCCOPY)!=FALSE,"Actual GDI surface BitBlt failed");
    SelectObject(memory,previous);DeleteObject(bitmap);DeleteDC(memory);
    oapiReleaseDC(surface,dc);contextCheck();
    dc=oapiGetDC(surface);require(dc!=nullptr,"Uploaded surface cannot be acquired again");contextCheck();
    for(int y=0;y<7;++y)for(int x=0;x<13;++x)
        require(GetPixel(dc,x,y)==color(x,y,repeat),"GDI/GPU round-trip pixel or row order differs");
    oapiReleaseDC(surface,dc);contextCheck();
    if(foreign)foreign->Restore();
    state.Check();
    // The result must also survive the renderer's actual GPU blit path.
    SURFHANDLE target=oapiCreateSurface(19,11);require(target!=nullptr,"Actual blit target creation failed");
    oapiBlt(target,surface,2,1,0,0,13,7);
    dc=oapiGetDC(target);require(dc!=nullptr,"GPU blit target has no GDI DC");
    for(int y=0;y<7;++y)for(int x=0;x<13;++x)
        require(GetPixel(dc,x+2,y+1)==color(x,y,repeat),"GDI/GPU blit pixel or offset differs");
    oapiReleaseDC(target,dc);state.Check();
    oapiDestroySurface(target);oapiDestroySurface(surface);
    require(glGetError()==GL_NO_ERROR,"Actual GDI integration produced an OpenGL error");
}

void offscreenReadback() {
    const HDC parentDC=wglGetCurrentDC();const HGLRC parentContext=wglGetCurrentContext();
    {
        dragonfly::WglBitmapTarget target(13,7);
        require(wglGetCurrentDC()==parentDC && wglGetCurrentContext()==parentContext,
                "Actual ADI target creation changed its caller context");
        {
            dragonfly::WglContextRestore active(target.RenderDC(),target.Context());
            glViewport(0,0,13,7);
            // Exercise the actual compatibility command path used by the ADI.
            glMatrixMode(GL_PROJECTION);glLoadIdentity();
            glMatrixMode(GL_MODELVIEW);glLoadIdentity();
            const GLuint list=glGenLists(1);require(list!=0,"Actual ADI compatibility display list failed");
            glNewList(list,GL_COMPILE);glClearColor(0,0,1,1);glClear(GL_COLOR_BUFFER_BIT);glEndList();
            glCallList(list);glDeleteLists(list,1);
            glEnable(GL_SCISSOR_TEST);glScissor(0,0,13,3);
            glClearColor(1,0,0,1);glClear(GL_COLOR_BUFFER_BIT);glDisable(GL_SCISSOR_TEST);
            glFinish();target.Readback();
            for(int y=0;y<7;++y)for(int x=0;x<13;++x)
                require(GetPixel(target.BitmapDC(),x,y)==(y<4?RGB(0,0,255):RGB(255,0,0)),
                        "Actual ADI framebuffer/DIB color or vertical orientation differs");
        }
        require(wglGetCurrentDC()==parentDC && wglGetCurrentContext()==parentContext,
                "Actual ADI drawing changed its caller context");
    }
    require(wglGetCurrentDC()==parentDC && wglGetCurrentContext()==parentContext,
            "Actual ADI target destruction changed its caller context");
}

class Driver final:public oapi::Module {
public:
    explicit Driver(HINSTANCE instance):Module(instance) {}
    void clbkSimulationStart(RenderMode mode) override {
        try {
            require(mode!=RENDER_NONE,"Actual window renderer required");
            CompatibilityContext foreign;
            roundtrip(0,nullptr);roundtrip(1,&foreign);offscreenReadback(); // Complete one-time driver allocation first.
            const DWORD before=GetGuiResources(GetCurrentProcess(),GR_GDIOBJECTS);
            require(before>0,"Actual GDI object count unavailable");
            for(unsigned repeat=0;repeat<100;++repeat)roundtrip(repeat,repeat%2?&foreign:nullptr);
            offscreenReadback();
            const DWORD after=GetGuiResources(GetCurrentProcess(),GR_GDIOBJECTS);
            require(after<=before,"Actual GDI surface DC/bitmap objects leaked");
            std::ofstream result("surface-dc-result.json");
            result<<"{\"status\":\"passed\",\"roundtrips\":100,\"pixel_checks\":18200,"
                  <<"\"foreign_context_roundtrips\":50,\"offscreen_target_readbacks\":2,\"gdi_objects_before\":"<<before
                  <<",\"gdi_objects_after\":"<<after<<"}\n";
        } catch(const std::exception& error) {
            std::fprintf(stderr,"Windows surface controls: %s\n",error.what());std::fflush(stderr);
            std::ofstream("surface-dc-failure.txt")<<error.what()<<'\n';std::exit(42);
        }
    }
};
Driver* driver=nullptr;
}
DLLCLBK void InitModule(HINSTANCE instance) {driver=new Driver(instance);oapiRegisterModule(driver);}
DLLCLBK void ExitModule(HINSTANCE) {delete driver;driver=nullptr;}
