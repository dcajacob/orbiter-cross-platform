// Licensed under the MIT License
// Real public SDK/GDI/OpenGL calls in the production Windows application.
#define ORBITER_MODULE
#include "Orbitersdk.h"
#include <GL/gl.h>
#include <cstdlib>
#include <fstream>
#include <stdexcept>

namespace {
void require(bool value,const char* message) {if(!value)throw std::runtime_error(message);}

class BitmapContext {
    HDC previousDC=wglGetCurrentDC();
    HGLRC previousContext=wglGetCurrentContext();
    HDC dc=nullptr;
    HBITMAP bitmap=nullptr;
    HGDIOBJ previousBitmap=nullptr;
    HGLRC context=nullptr;
public:
    BitmapContext() {
        require(previousDC && previousContext,"Actual client context is missing");
        dc=CreateCompatibleDC(previousDC);require(dc!=nullptr,"Compatibility DC failed");
        BITMAPINFO info{};info.bmiHeader.biSize=sizeof(BITMAPINFOHEADER);
        info.bmiHeader.biWidth=16;info.bmiHeader.biHeight=16;
        info.bmiHeader.biPlanes=1;info.bmiHeader.biBitCount=32;info.bmiHeader.biCompression=BI_RGB;
        void* bits=nullptr;bitmap=CreateDIBSection(dc,&info,DIB_RGB_COLORS,&bits,nullptr,0);
        require(bitmap && bits,"Compatibility DIB failed");
        previousBitmap=SelectObject(dc,bitmap);require(previousBitmap && previousBitmap!=HGDI_ERROR,"Compatibility bitmap selection failed");
        PIXELFORMATDESCRIPTOR format{};format.nSize=sizeof(format);format.nVersion=1;
        format.dwFlags=PFD_DRAW_TO_BITMAP|PFD_SUPPORT_OPENGL|PFD_SUPPORT_GDI;
        format.iPixelType=PFD_TYPE_RGBA;format.cColorBits=32;
        const int index=ChoosePixelFormat(dc,&format);
        require(index && SetPixelFormat(dc,index,&format),"Compatibility pixel format failed");
        context=wglCreateContext(dc);require(context!=nullptr,"Compatibility OpenGL context failed");
    }
    void Activate() {require(wglMakeCurrent(dc,context)!=FALSE,"Compatibility context acquisition failed");}
    void Restore() {require(wglMakeCurrent(previousDC,previousContext)!=FALSE,"Actual client context restoration failed");}
    HGLRC Context() const {return context;}
    HDC DC() const {return dc;}
    ~BitmapContext() {
        wglMakeCurrent(previousDC,previousContext);
        if(context)wglDeleteContext(context);
        if(dc && previousBitmap)SelectObject(dc,previousBitmap);
        if(bitmap)DeleteObject(bitmap);
        if(dc)DeleteDC(dc);
    }
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

void roundtrip(unsigned repeat,BitmapContext* foreign) {
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
    require(oapiBlt(target,surface,2,1,0,0,13,7)!=FALSE,"Actual GPU surface blit failed");
    dc=oapiGetDC(target);require(dc!=nullptr,"GPU blit target has no GDI DC");
    for(int y=0;y<7;++y)for(int x=0;x<13;++x)
        require(GetPixel(dc,x+2,y+1)==color(x,y,repeat),"GDI/GPU blit pixel or offset differs");
    oapiReleaseDC(target,dc);state.Check();
    oapiDestroySurface(target);oapiDestroySurface(surface);
    require(glGetError()==GL_NO_ERROR,"Actual GDI integration produced an OpenGL error");
}

class Driver final:public oapi::Module {
public:
    explicit Driver(HINSTANCE instance):Module(instance) {}
    void clbkSimulationStart(RenderMode mode) override {
        try {
            require(mode!=RENDER_NONE,"Actual window renderer required");
            BitmapContext foreign;
            roundtrip(0,nullptr);roundtrip(1,&foreign); // Complete one-time driver allocation first.
            const DWORD before=GetGuiResources(GetCurrentProcess(),GR_GDIOBJECTS);
            require(before>0,"Actual GDI object count unavailable");
            for(unsigned repeat=0;repeat<100;++repeat)roundtrip(repeat,repeat%2?&foreign:nullptr);
            const DWORD after=GetGuiResources(GetCurrentProcess(),GR_GDIOBJECTS);
            require(after<=before,"Actual GDI surface DC/bitmap objects leaked");
            std::ofstream result("surface-dc-result.json");
            result<<"{\"status\":\"passed\",\"roundtrips\":100,\"pixel_checks\":18200,"
                  <<"\"foreign_context_roundtrips\":50,\"gdi_objects_before\":"<<before
                  <<",\"gdi_objects_after\":"<<after<<"}\n";
        } catch(const std::exception& error) {
            std::ofstream("surface-dc-failure.txt")<<error.what()<<'\n';std::exit(42);
        }
    }
};
Driver* driver=nullptr;
}
DLLCLBK void InitModule(HINSTANCE instance) {driver=new Driver(instance);oapiRegisterModule(driver);}
DLLCLBK void ExitModule(HINSTANCE) {delete driver;driver=nullptr;}
