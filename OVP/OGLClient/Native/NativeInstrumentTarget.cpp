// Licensed under the MIT License
#include "glad.h"
#include "OGLClient.h"
#include "Texture.h"
#include <GLFW/glfw3.h>
#include <cstdio>
#include <exception>
#include <memory>
#include <stdexcept>

using namespace orbiter::production;
namespace {
void require(bool value,const char* message) {if(!value)throw std::runtime_error(message);}

class ContextRestore final:public NativeGraphicsContext {
    GLFWwindow* previous=glfwGetCurrentContext();
public:
    void Discard(GLFWwindow* removed) {if(previous==removed)previous=nullptr;}
    ~ContextRestore() override {
        glfwMakeContextCurrent(previous);
        if(glfwGetCurrentContext()!=previous) {
            std::fputs("Native instrument context restoration failed\n",stderr);
            std::terminate();
        }
    }
};

class PixelTransfer {
    GLenum target,binding;
    GLenum parameters[8];
    GLint values[8]{},previousActive=0,texture=0,buffer=0;
public:
    explicit PixelTransfer(bool reading):target(reading?GL_PIXEL_PACK_BUFFER:GL_PIXEL_UNPACK_BUFFER),
        binding(reading?GL_PIXEL_PACK_BUFFER_BINDING:GL_PIXEL_UNPACK_BUFFER_BINDING) {
        const GLenum pack[]={GL_PACK_ALIGNMENT,GL_PACK_ROW_LENGTH,GL_PACK_SKIP_PIXELS,GL_PACK_SKIP_ROWS,
                             GL_PACK_IMAGE_HEIGHT,GL_PACK_SKIP_IMAGES,GL_PACK_SWAP_BYTES,GL_PACK_LSB_FIRST};
        const GLenum unpack[]={GL_UNPACK_ALIGNMENT,GL_UNPACK_ROW_LENGTH,GL_UNPACK_SKIP_PIXELS,GL_UNPACK_SKIP_ROWS,
                               GL_UNPACK_IMAGE_HEIGHT,GL_UNPACK_SKIP_IMAGES,GL_UNPACK_SWAP_BYTES,GL_UNPACK_LSB_FIRST};
        glGetIntegerv(GL_ACTIVE_TEXTURE,&previousActive);glActiveTexture(GL_TEXTURE0);
        glGetIntegerv(GL_TEXTURE_BINDING_2D,&texture);glGetIntegerv(binding,&buffer);glBindBuffer(target,0);
        for(unsigned i=0;i<8;++i) {
            parameters[i]=reading?pack[i]:unpack[i];glGetIntegerv(parameters[i],&values[i]);
            glPixelStorei(parameters[i],i?0:1);
        }
    }
    ~PixelTransfer() {
        for(unsigned i=0;i<8;++i)glPixelStorei(parameters[i],values[i]);
        glBindBuffer(target,buffer);glBindTexture(GL_TEXTURE_2D,texture);glActiveTexture(previousActive);
    }
};

class InstrumentTarget final:public NativeInstrumentTarget {
    GLFWwindow* window=nullptr;
    GLuint framebuffer=0,color=0;
    int width,height;

    void Close() noexcept {
        if(!window)return;
        ContextRestore restore;restore.Discard(window);
        glfwMakeContextCurrent(window);
        if(glfwGetCurrentContext()!=window) {
            std::fputs("Native instrument cleanup context failed\n",stderr);std::terminate();
        }
        if(framebuffer)glDeleteFramebuffers(1,&framebuffer);
        if(color)glDeleteRenderbuffers(1,&color);
        framebuffer=color=0;glfwMakeContextCurrent(nullptr);glfwDestroyWindow(window);window=nullptr;
    }
public:
    InstrumentTarget(int w,int h):width(w),height(h) {
        require(width>0 && height>0 && width<=16384 && height<=16384,"Invalid native instrument dimensions");
        ContextRestore restore;
        require(glfwGetCurrentContext()!=nullptr,"Native instrument requires the active renderer context");
        // The renderer owns GLFW's window configuration. Restore its declared
        // 3.3 core/visible/24-bit-depth/8-bit-stencil policy after this creation.
        struct RestoreWindowHints {
            ~RestoreWindowHints() {
                glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR,3);glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR,3);
                glfwWindowHint(GLFW_OPENGL_PROFILE,GLFW_OPENGL_CORE_PROFILE);glfwWindowHint(GLFW_VISIBLE,GLFW_TRUE);
                glfwWindowHint(GLFW_DEPTH_BITS,24);glfwWindowHint(GLFW_STENCIL_BITS,8);
            }
        } hints;
        try {
            glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR,3);glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR,3);
            glfwWindowHint(GLFW_OPENGL_PROFILE,GLFW_OPENGL_COMPAT_PROFILE);glfwWindowHint(GLFW_VISIBLE,GLFW_FALSE);
            // Match the original instrument's request for no depth/stencil bits.
            glfwWindowHint(GLFW_DEPTH_BITS,0);glfwWindowHint(GLFW_STENCIL_BITS,0);
            window=glfwCreateWindow(width,height,"Orbiter instrument compatibility target",nullptr,nullptr);
            require(window!=nullptr,"Native instrument compatibility context creation failed");
            glfwMakeContextCurrent(window);require(glfwGetCurrentContext()==window,"Native instrument activation failed");
            glGenFramebuffers(1,&framebuffer);glBindFramebuffer(GL_FRAMEBUFFER,framebuffer);
            // The original ADI deliberately binds texture name 1. A color
            // renderbuffer keeps its texture storage separate from the target.
            glGenRenderbuffers(1,&color);glBindRenderbuffer(GL_RENDERBUFFER,color);
            glRenderbufferStorage(GL_RENDERBUFFER,GL_RGBA8,width,height);
            glFramebufferRenderbuffer(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_RENDERBUFFER,color);
            glDrawBuffer(GL_COLOR_ATTACHMENT0);glReadBuffer(GL_COLOR_ATTACHMENT0);
            require(glCheckFramebufferStatus(GL_FRAMEBUFFER)==GL_FRAMEBUFFER_COMPLETE && glGetError()==GL_NO_ERROR,
                    "Native instrument offscreen framebuffer creation failed");
        } catch(...) {Close();throw;}
    }
    ~InstrumentTarget() override {Close();}
    void Activate() override {
        glfwMakeContextCurrent(window);require(glfwGetCurrentContext()==window,"Native instrument activation failed");
        glBindFramebuffer(GL_FRAMEBUFFER,framebuffer);
    }
    void Readback(std::vector<std::uint8_t>& pixels) override {
        require(glfwGetCurrentContext()==window,"Native instrument readback requires its own context");
        pixels.resize(std::size_t(width)*std::size_t(height)*4);
        PixelTransfer transfer(true);GLint previousFramebuffer=0,previousBuffer=0;
        glGetIntegerv(GL_READ_FRAMEBUFFER_BINDING,&previousFramebuffer);glGetIntegerv(GL_READ_BUFFER,&previousBuffer);
        glBindFramebuffer(GL_READ_FRAMEBUFFER,framebuffer);glReadBuffer(GL_COLOR_ATTACHMENT0);
        glReadPixels(0,0,width,height,GL_RGBA,GL_UNSIGNED_BYTE,pixels.data());
        const GLenum error=glGetError();
        glBindFramebuffer(GL_READ_FRAMEBUFFER,previousFramebuffer);glReadBuffer(previousBuffer);
        require(error==GL_NO_ERROR,"Native instrument framebuffer readback failed");
    }
};
}

std::unique_ptr<NativeGraphicsContext> OGLClient::SaveGraphicsContext() {return std::make_unique<ContextRestore>();}
std::unique_ptr<NativeInstrumentTarget> OGLClient::CreateInstrumentTarget(int width,int height) {
    return std::make_unique<InstrumentTarget>(width,height);
}
bool OGLClient::UploadSurfacePixels(SURFHANDLE surface,int width,int height,const std::vector<std::uint8_t>& pixels) {
    if(!surface || width<=0 || height<=0 || pixels.size()!=std::size_t(width)*std::size_t(height)*4)return false;
    auto* texture=static_cast<OGLTexture*>(surface);
    if(texture->m_Width!=width || texture->m_Height!=height)return false;
    PixelTransfer transfer(false);glBindTexture(GL_TEXTURE_2D,texture->m_TexId);
    glTexSubImage2D(GL_TEXTURE_2D,0,0,0,width,height,GL_RGBA,GL_UNSIGNED_BYTE,pixels.data());
    return glGetError()==GL_NO_ERROR;
}
