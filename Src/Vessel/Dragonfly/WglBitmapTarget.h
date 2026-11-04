// Licensed under the MIT License
// Real compatibility-profile rendering and GDI readback for the legacy ADI.
#pragma once
#include <windows.h>
#include <GL/gl.h>
#include <cstdint>
#include <stdexcept>
#include "WglContext.h"

namespace dragonfly {
class WglBitmapTarget {
    static constexpr GLenum framebufferTarget=0x8D40;
    static constexpr GLenum colorAttachment=0x8CE0;
    static constexpr GLenum framebufferComplete=0x8CD5;
    using GenFramebuffers=void (APIENTRY*)(GLsizei,GLuint*);
    using BindFramebuffer=void (APIENTRY*)(GLenum,GLuint);
    using FramebufferTexture=void (APIENTRY*)(GLenum,GLenum,GLenum,GLuint,GLint);
    using CheckFramebuffer=GLenum (APIENTRY*)(GLenum);
    using DeleteFramebuffers=void (APIENTRY*)(GLsizei,const GLuint*);
    HWND window=nullptr;
    HDC renderDC=nullptr,memoryDC=nullptr;
    HGLRC context=nullptr;
    HBITMAP bitmap=nullptr;
    HGDIOBJ previousBitmap=nullptr;
    void* pixels=nullptr;
    GLuint framebuffer=0,color=0;
    int width,height;
    BindFramebuffer bindFramebuffer=nullptr;
    DeleteFramebuffers deleteFramebuffers=nullptr;

    static void require(bool value,const char* message) {if(!value)throw std::runtime_error(message);}
    class WindowClass {
        HINSTANCE instance=nullptr;
        bool owned=false;
    public:
        static const wchar_t* Name() {return L"Orbiter.StockDragonfly.ADI.Compatibility";}
        WindowClass() {
            require(GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
                                      Name(),&instance)!=FALSE,"Dragonfly window module lookup failed");
            WNDCLASSEXW type{};type.cbSize=sizeof(type);type.style=CS_OWNDC;
            type.lpfnWndProc=DefWindowProcW;type.hInstance=instance;type.lpszClassName=Name();
            owned=RegisterClassExW(&type)!=0;
            if(!owned) {
                WNDCLASSEXW existing{};existing.cbSize=sizeof(existing);
                require(GetLastError()==ERROR_CLASS_ALREADY_EXISTS && GetClassInfoExW(instance,Name(),&existing) &&
                        existing.lpfnWndProc==DefWindowProcW && (existing.style&CS_OWNDC),
                        "Dragonfly compatibility window class failed");
            }
        }
        HINSTANCE Instance() const {return instance;}
        ~WindowClass() {if(owned)UnregisterClassW(Name(),instance);}
    };
    template<class Function>static Function procedure(const char* name,const char* extension) {
        auto pointer=wglGetProcAddress(name);
        auto valid=[](PROC value) {
            const auto address=reinterpret_cast<std::uintptr_t>(value);
            return address>3 && address!=static_cast<std::uintptr_t>(-1);
        };
        if(!valid(pointer))pointer=wglGetProcAddress(extension);
        require(valid(pointer),"Dragonfly framebuffer entry point unavailable");
        return reinterpret_cast<Function>(pointer);
    }
    void release() noexcept {
        WglContextRestore restore;restore.Discard(context);
        if(context && wglMakeCurrent(renderDC,context)) {
            if(framebuffer && deleteFramebuffers)deleteFramebuffers(1,&framebuffer);
            if(color)glDeleteTextures(1,&color);
        }
        if(context){wglMakeCurrent(nullptr,nullptr);wglDeleteContext(context);context=nullptr;}
        if(renderDC && window){ReleaseDC(window,renderDC);renderDC=nullptr;}
        if(window){DestroyWindow(window);window=nullptr;}
        if(memoryDC && previousBitmap)SelectObject(memoryDC,previousBitmap);
        if(bitmap){DeleteObject(bitmap);bitmap=nullptr;}
        if(memoryDC){DeleteDC(memoryDC);memoryDC=nullptr;}
    }
public:
    WglBitmapTarget(int w,int h):width(w),height(h) {
        WglContextRestore restore;
        try {
            static WindowClass type;
            window=CreateWindowExW(WS_EX_TOOLWINDOW|WS_EX_NOACTIVATE,WindowClass::Name(),L"",WS_POPUP,
                                  0,0,width,height,nullptr,nullptr,type.Instance(),nullptr);
            require(window!=nullptr,"Dragonfly compatibility window failed");
            renderDC=GetDC(window);require(renderDC!=nullptr,"Dragonfly compatibility window DC failed");
            PIXELFORMATDESCRIPTOR format{};format.nSize=sizeof(format);format.nVersion=1;
            format.dwFlags=PFD_DRAW_TO_WINDOW|PFD_SUPPORT_OPENGL;format.iPixelType=PFD_TYPE_RGBA;
            format.cColorBits=32;
            const int index=ChoosePixelFormat(renderDC,&format);
            require(index && SetPixelFormat(renderDC,index,&format),"Dragonfly compatibility pixel format failed");
            context=wglCreateContext(renderDC);
            require(context && wglMakeCurrent(renderDC,context),"Dragonfly compatibility context failed");
            auto generate=procedure<GenFramebuffers>("glGenFramebuffers","glGenFramebuffersEXT");
            bindFramebuffer=procedure<BindFramebuffer>("glBindFramebuffer","glBindFramebufferEXT");
            auto attach=procedure<FramebufferTexture>("glFramebufferTexture2D","glFramebufferTexture2DEXT");
            auto check=procedure<CheckFramebuffer>("glCheckFramebufferStatus","glCheckFramebufferStatusEXT");
            deleteFramebuffers=procedure<DeleteFramebuffers>("glDeleteFramebuffers","glDeleteFramebuffersEXT");
            glGenTextures(1,&color);glBindTexture(GL_TEXTURE_2D,color);
            glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_LINEAR);
            glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_LINEAR);
            glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA,width,height,0,GL_RGBA,GL_UNSIGNED_BYTE,nullptr);
            generate(1,&framebuffer);bindFramebuffer(framebufferTarget,framebuffer);
            attach(framebufferTarget,colorAttachment,GL_TEXTURE_2D,color,0);
            // The original bitmap format requests zero depth/stencil bits.
            glDrawBuffer(colorAttachment);glReadBuffer(colorAttachment);
            require(check(framebufferTarget)==framebufferComplete && glGetError()==GL_NO_ERROR,
                    "Dragonfly offscreen framebuffer failed");
            memoryDC=CreateCompatibleDC(renderDC);require(memoryDC!=nullptr,"Dragonfly bitmap memory DC failed");
            BITMAPINFO info{};info.bmiHeader.biSize=sizeof(BITMAPINFOHEADER);
            info.bmiHeader.biWidth=width;info.bmiHeader.biHeight=height;
            info.bmiHeader.biPlanes=1;info.bmiHeader.biBitCount=32;info.bmiHeader.biCompression=BI_RGB;
            bitmap=CreateDIBSection(memoryDC,&info,DIB_RGB_COLORS,&pixels,nullptr,0);
            require(bitmap && pixels,"Dragonfly readback bitmap failed");
            HGDIOBJ previous=SelectObject(memoryDC,bitmap);
            require(previous && previous!=HGDI_ERROR,"Dragonfly readback bitmap selection failed");
            previousBitmap=previous;
        } catch(...) {release();throw;}
    }
    WglBitmapTarget(const WglBitmapTarget&)=delete;
    WglBitmapTarget& operator=(const WglBitmapTarget&)=delete;
    ~WglBitmapTarget() {release();}
    HDC RenderDC() const {return renderDC;}
    HDC BitmapDC() const {return memoryDC;}
    HGLRC Context() const {return context;}
    HBITMAP Bitmap() const {return bitmap;}
    HGDIOBJ PreviousBitmap() const {return previousBitmap;}
    void Activate() const {require(wglMakeCurrent(renderDC,context)!=FALSE,"Dragonfly render context acquisition failed");}
    void Readback() const {
        require(GdiFlush()!=FALSE,"Dragonfly previous bitmap copy did not complete");
        bindFramebuffer(framebufferTarget,framebuffer);
        glPixelStorei(GL_PACK_ALIGNMENT,4);glPixelStorei(GL_PACK_ROW_LENGTH,0);
        glPixelStorei(GL_PACK_SKIP_PIXELS,0);glPixelStorei(GL_PACK_SKIP_ROWS,0);
        // Both GL readback and the positive-height DIB start at the bottom row.
        glReadPixels(0,0,width,height,0x80E1 /* GL_BGRA */,GL_UNSIGNED_BYTE,pixels);
        require(glGetError()==GL_NO_ERROR,"Dragonfly framebuffer readback failed");
    }
};
}
