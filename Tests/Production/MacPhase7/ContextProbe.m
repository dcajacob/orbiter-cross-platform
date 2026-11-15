#import <AppKit/AppKit.h>
#import <OpenGL/gl3.h>
#include <stdbool.h>
#include <stdio.h>

static bool probe(const char *name, NSOpenGLPixelFormatAttribute profile,
                  bool accelerated, bool offline, bool standardWindow)
{
    NSOpenGLPixelFormatAttribute attributes[16];
    size_t i = 0;
    attributes[i++] = NSOpenGLPFAOpenGLProfile;
    attributes[i++] = profile;
    if (accelerated) attributes[i++] = NSOpenGLPFAAccelerated;
    if (offline) attributes[i++] = NSOpenGLPFAAllowOfflineRenderers;
    if (standardWindow) {
        attributes[i++] = NSOpenGLPFADoubleBuffer;
        attributes[i++] = NSOpenGLPFAColorSize;
        attributes[i++] = 24;
        attributes[i++] = NSOpenGLPFAAlphaSize;
        attributes[i++] = 8;
        attributes[i++] = NSOpenGLPFADepthSize;
        attributes[i++] = 24;
        attributes[i++] = NSOpenGLPFAStencilSize;
        attributes[i++] = 8;
    }
    attributes[i] = 0;

    NSOpenGLPixelFormat *format = [[NSOpenGLPixelFormat alloc] initWithAttributes:attributes];
    if (!format) {
        printf("%s: no pixel format\n", name);
        return false;
    }
    NSOpenGLContext *context = [[NSOpenGLContext alloc] initWithFormat:format shareContext:nil];
    if (!context) {
        printf("%s: pixel format available, context creation failed\n", name);
        return false;
    }
    [context makeCurrentContext];
    GLint hardware = 0;
    [format getValues:&hardware forAttribute:NSOpenGLPFAAccelerated forVirtualScreen:0];
    const GLubyte *version = glGetString(GL_VERSION);
    const GLubyte *renderer = glGetString(GL_RENDERER);
    printf("%s: accelerated=%d version=%s renderer=%s\n", name, hardware,
           version ? (const char *)version : "(unknown)",
           renderer ? (const char *)renderer : "(unknown)");
    [NSOpenGLContext clearCurrentContext];
    return version && renderer;
}

int main(void)
{
    @autoreleasepool {
        [NSApplication sharedApplication];
        probe("4.1 accelerated window", NSOpenGLProfileVersion4_1Core, true, false, true);
        probe("4.1 accelerated minimal", NSOpenGLProfileVersion4_1Core, true, false, false);
        probe("4.1 offline accelerated", NSOpenGLProfileVersion4_1Core, true, true, false);
        probe("4.1 any renderer", NSOpenGLProfileVersion4_1Core, false, true, false);
        probe("3.2 any renderer", NSOpenGLProfileVersion3_2Core, false, true, false);
        probe("legacy any renderer", NSOpenGLProfileVersionLegacy, false, true, false);
    }
    return 0;
}
