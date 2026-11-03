#define GL_GLEXT_PROTOTYPES
#include <EGL/egl.h>
#include <EGL/eglext.h>
#include <GL/gl.h>
#include <GL/glext.h>
#include <cstdio>
#include <vector>
extern "C" int run(bool mipmap) {
    auto getDisplay=reinterpret_cast<PFNEGLGETPLATFORMDISPLAYEXTPROC>(eglGetProcAddress("eglGetPlatformDisplayEXT"));
    if(!getDisplay)return 2;
    EGLDisplay display=getDisplay(EGL_PLATFORM_SURFACELESS_MESA,EGL_DEFAULT_DISPLAY,nullptr);
    if(display==EGL_NO_DISPLAY || !eglInitialize(display,nullptr,nullptr))return 3;
    if(!eglBindAPI(EGL_OPENGL_API))return 4;
    const EGLint attrs[]={EGL_SURFACE_TYPE,EGL_PBUFFER_BIT,EGL_RENDERABLE_TYPE,EGL_OPENGL_BIT,EGL_NONE};
    EGLConfig config{};EGLint count=0;
    if(!eglChooseConfig(display,attrs,&config,1,&count) || count!=1)return 5;
    const EGLint ctxattrs[]={EGL_CONTEXT_MAJOR_VERSION,3,EGL_CONTEXT_MINOR_VERSION,3,EGL_CONTEXT_OPENGL_PROFILE_MASK,EGL_CONTEXT_OPENGL_CORE_PROFILE_BIT,EGL_NONE};
    EGLContext context=eglCreateContext(display,config,EGL_NO_CONTEXT,ctxattrs);
    if(context==EGL_NO_CONTEXT || !eglMakeCurrent(display,EGL_NO_SURFACE,EGL_NO_SURFACE,context))return 6;
    std::printf("GL_VERSION=%s\nGL_RENDERER=%s\n",glGetString(GL_VERSION),glGetString(GL_RENDERER));
    GLuint texture=0;glGenTextures(1,&texture);glBindTexture(GL_TEXTURE_2D,texture);
    std::vector<unsigned char> pixels(256*256*4,127);
    glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA8,256,256,0,GL_RGBA,GL_UNSIGNED_BYTE,pixels.data());
    if(mipmap){
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_LINEAR_MIPMAP_LINEAR);
        glGenerateMipmap(GL_TEXTURE_2D);
        GLint width=0;glGetTexLevelParameteriv(GL_TEXTURE_2D,1,GL_TEXTURE_WIDTH,&width);
        if(width!=128)return 7;
    }
    glFinish();const GLenum error=glGetError();glDeleteTextures(1,&texture);
    if(!eglMakeCurrent(display,EGL_NO_SURFACE,EGL_NO_SURFACE,EGL_NO_CONTEXT) || !eglDestroyContext(display,context) || !eglTerminate(display) || !eglReleaseThread())return 8;
    std::printf("mipmap=%d gl_error=%u context_destroyed=true\n",mipmap,error);std::fflush(stdout);
    return error?9:0;
}
