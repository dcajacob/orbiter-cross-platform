// Copyright (c) Orbiter contributors. Licensed under the MIT License.
// Test the real Windows window/WGL/C interface, independently of Orbiter's POC.
#include <windows.h>
#include <psapi.h>
#include <GL/gl.h>
#include <array>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
void require(bool test, const char *message) {
    if (!test) throw std::runtime_error(std::string(message) + " (Win32=" + std::to_string(GetLastError()) + ")");
}
template <class T> T entry(const char *name) {
    auto p = wglGetProcAddress(name);
    require(p && p != reinterpret_cast<PROC>(1) && p != reinterpret_cast<PROC>(2) &&
        p != reinterpret_cast<PROC>(3) && p != reinterpret_cast<PROC>(-1), name);
    return reinterpret_cast<T>(p);
}
// Only OpenGL C ABI types cross the MSVC / Mesa UCRT boundary.
#define GL_ENTRIES(F) \
    F(GLuint, CreateShader, (GLenum)) \
    F(void, ShaderSource, (GLuint, GLsizei, const char *const *, const GLint *)) \
    F(void, CompileShader, (GLuint)) \
    F(void, GetShaderiv, (GLuint, GLenum, GLint *)) \
    F(void, GetShaderInfoLog, (GLuint, GLsizei, GLsizei *, char *)) \
    F(GLuint, CreateProgram, ()) \
    F(void, AttachShader, (GLuint, GLuint)) \
    F(void, LinkProgram, (GLuint)) \
    F(void, GetProgramiv, (GLuint, GLenum, GLint *)) \
    F(void, GetProgramInfoLog, (GLuint, GLsizei, GLsizei *, char *)) \
    F(void, UseProgram, (GLuint)) \
    F(void, DeleteProgram, (GLuint)) \
    F(void, DeleteShader, (GLuint)) \
    F(void, GenVertexArrays, (GLsizei, GLuint *)) \
    F(void, BindVertexArray, (GLuint)) \
    F(void, DeleteVertexArrays, (GLsizei, const GLuint *)) \
    F(void, GenFramebuffers, (GLsizei, GLuint *)) \
    F(void, BindFramebuffer, (GLenum, GLuint)) \
    F(void, FramebufferTexture2D, (GLenum, GLenum, GLenum, GLuint, GLint)) \
    F(GLenum, CheckFramebufferStatus, (GLenum)) \
    F(void, BlitFramebuffer, (GLint, GLint, GLint, GLint, GLint, GLint, GLint, GLint, GLbitfield, GLenum)) \
    F(void, DeleteFramebuffers, (GLsizei, const GLuint *))
struct GL {
#define DECLARE(result, name, args) using name##Fn = result(APIENTRY *)args; name##Fn name = entry<name##Fn>("gl" #name);
    GL_ENTRIES(DECLARE)
#undef DECLARE
};
LRESULT CALLBACK windowProc(HWND window, UINT message, WPARAM wparam, LPARAM lparam) {
    return DefWindowProcW(window, message, wparam, lparam);
}
void events() {
    MSG message;
    while (PeekMessageW(&message, nullptr, 0, 0, PM_REMOVE)) {
        TranslateMessage(&message);
        DispatchMessageW(&message);
    }
}
struct Window {
    HWND window = nullptr;
    HDC dc = nullptr;
    HGLRC context = nullptr;
    Window() {
        WNDCLASSW cls{};
        cls.style = CS_OWNDC;
        cls.lpfnWndProc = windowProc;
        cls.hInstance = GetModuleHandleW(nullptr);
        cls.lpszClassName = L"OrbiterProductionWGLProbe";
        require(RegisterClassW(&cls) || GetLastError() == ERROR_CLASS_ALREADY_EXISTS, "RegisterClass");
        window = CreateWindowW(cls.lpszClassName, L"Orbiter production WGL probe", WS_OVERLAPPEDWINDOW | WS_VISIBLE,
            CW_USEDEFAULT, CW_USEDEFAULT, 640, 480, nullptr, nullptr, cls.hInstance, nullptr);
        require(window != nullptr, "CreateWindow");
        dc = GetDC(window);
        require(dc != nullptr, "GetDC");
        PIXELFORMATDESCRIPTOR format{};
        format.nSize = sizeof(format);
        format.nVersion = 1;
        format.dwFlags = PFD_DRAW_TO_WINDOW | PFD_SUPPORT_OPENGL | PFD_DOUBLEBUFFER;
        format.iPixelType = PFD_TYPE_RGBA;
        format.cColorBits = 32;
        format.cDepthBits = 24;
        const int index = ChoosePixelFormat(dc, &format);
        require(index && SetPixelFormat(dc, index, &format), "SetPixelFormat");
        context = wglCreateContext(dc);
        require(context && wglMakeCurrent(dc, context), "legacy WGL context");
        using Create = HGLRC(WINAPI *)(HDC, HGLRC, const int *);
        auto create = entry<Create>("wglCreateContextAttribsARB");
        const int attributes[] = {0x2091, 3, 0x2092, 3, 0x9126, 1, 0}; // 3.3 core
        HGLRC core = create(dc, nullptr, attributes);
        require(core != nullptr, "WGL 3.3 core context");
        require(wglMakeCurrent(nullptr, nullptr) && wglDeleteContext(context), "legacy context shutdown");
        context = core;
        require(wglMakeCurrent(dc, context) != FALSE, "make core context current");
        events();
    }
    void close() {
        require(wglMakeCurrent(nullptr, nullptr) && wglDeleteContext(context), "core context shutdown");
        context = nullptr;
        require(ReleaseDC(window, dc) != 0, "ReleaseDC");
        dc = nullptr;
        require(DestroyWindow(window) != FALSE, "DestroyWindow");
        window = nullptr;
        events();
    }
    ~Window() {
        if (context) { wglMakeCurrent(nullptr, nullptr); wglDeleteContext(context); }
        if (dc) ReleaseDC(window, dc);
        if (window) DestroyWindow(window);
    }
};
GLuint shader(GL &gl, GLenum type, const char *source) {
    GLuint handle = gl.CreateShader(type);
    gl.ShaderSource(handle, 1, &source, nullptr);
    gl.CompileShader(handle);
    GLint ok = 0;
    gl.GetShaderiv(handle, 0x8B81, &ok);
    if (!ok) {
        char message[4096]{};
        gl.GetShaderInfoLog(handle, sizeof(message), nullptr, message);
        throw std::runtime_error(std::string("shader compilation: ") + message);
    }
    return handle;
}
void modules(const std::string &path) {
    std::array<HMODULE, 2048> handles{};
    DWORD bytes = 0;
    require(EnumProcessModules(GetCurrentProcess(), handles.data(), sizeof(handles), &bytes) != FALSE &&
        bytes <= sizeof(handles), "EnumProcessModules");
    std::ofstream output(path, std::ios::binary);
    for (DWORD i = 0; i < bytes / sizeof(HMODULE); ++i) {
        std::array<wchar_t, 32768> name{};
        DWORD count = GetModuleFileNameW(handles[i], name.data(), static_cast<DWORD>(name.size()));
        require(count && count < name.size(), "GetModuleFileName");
        int length = WideCharToMultiByte(CP_UTF8, 0, name.data(), count, nullptr, 0, nullptr, nullptr);
        std::string utf8(length, '\0');
        require(WideCharToMultiByte(CP_UTF8, 0, name.data(), count, utf8.data(), length, nullptr, nullptr) == length,
            "module path UTF-8 conversion");
        output << utf8 << '\n';
    }
    output.close();
    require(!output.fail(), "write loaded module paths");
}
void probe(int cycle, const std::string &prefix) {
    Window window;
    GL gl;
    const char *renderer = reinterpret_cast<const char *>(glGetString(GL_RENDERER));
    const char *version = reinterpret_cast<const char *>(glGetString(GL_VERSION));
    const char *vendor = reinterpret_cast<const char *>(glGetString(GL_VENDOR));
    require(renderer && version && vendor, "OpenGL driver strings");
    std::cout << "renderer=" << renderer << "\nversion=" << version << "\nvendor=" << vendor << '\n';
    require(std::string(renderer).find("llvmpipe") != std::string::npos, "software llvmpipe renderer required");
    GLint major = 0, minor = 0;
    glGetIntegerv(0x821B, &major);
    glGetIntegerv(0x821C, &minor);
    require(major > 3 || (major == 3 && minor >= 3), "OpenGL 3.3 required");
    GLuint vs = shader(gl, 0x8B31, "#version 330 core\nvoid main(){vec2 p[3]=vec2[3](vec2(-1,-1),vec2(3,-1),vec2(-1,3));gl_Position=vec4(p[gl_VertexID],0,1);}");
    GLuint fs = shader(gl, 0x8B30, "#version 330 core\nout vec4 color;void main(){color=vec4(0.25,0.5,0.75,1);}");
    GLuint program = gl.CreateProgram();
    gl.AttachShader(program, vs); gl.AttachShader(program, fs); gl.LinkProgram(program);
    GLint linked = 0;
    gl.GetProgramiv(program, 0x8B82, &linked);
    if (!linked) {
        char message[4096]{};
        gl.GetProgramInfoLog(program, sizeof(message), nullptr, message);
        throw std::runtime_error(std::string("program linking: ") + message);
    }
    GLuint vao = 0, fbo = 0, texture = 0;
    gl.GenVertexArrays(1, &vao); gl.BindVertexArray(vao);
    gl.GenFramebuffers(1, &fbo); gl.BindFramebuffer(0x8D40, fbo);
    glGenTextures(1, &texture); glBindTexture(GL_TEXTURE_2D, texture);
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, 32, 32, 0, GL_RGBA, GL_UNSIGNED_BYTE, nullptr);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
    gl.FramebufferTexture2D(0x8D40, 0x8CE0, GL_TEXTURE_2D, texture, 0);
    require(gl.CheckFramebufferStatus(0x8D40) == 0x8CD5, "complete framebuffer");
    glViewport(0, 0, 32, 32); gl.UseProgram(program); glDrawArrays(GL_TRIANGLES, 0, 3); glFinish();
    std::array<unsigned char, 32 * 32 * 4> pixels{};
    glReadPixels(0, 0, 32, 32, GL_RGBA, GL_UNSIGNED_BYTE, pixels.data());
    for (size_t i = 0; i < pixels.size(); i += 4)
        require(abs(int(pixels[i]) - 64) <= 1 && abs(int(pixels[i+1]) - 128) <= 1 &&
            abs(int(pixels[i+2]) - 191) <= 1 && pixels[i+3] == 255, "shader FBO pixel readback");
    std::ofstream image(prefix + "-" + std::to_string(cycle) + ".rgba", std::ios::binary);
    image.write(reinterpret_cast<const char *>(pixels.data()), pixels.size());
    image.close(); require(!image.fail(), "write FBO readback");
    for (int i = 0; i < 2; ++i) {
        require(SetWindowPos(window.window, nullptr, 0, 0, 640 + i*160, 480 + i*120,
            SWP_NOMOVE | SWP_NOZORDER) != FALSE, "resize window");
        events();
        RECT client{}; require(GetClientRect(window.window, &client) != FALSE, "client size");
        require(client.right > 0 && client.bottom > 0, "nonzero drawable");
        gl.BindFramebuffer(0x8CA8, fbo); gl.BindFramebuffer(0x8CA9, 0);
        gl.BlitFramebuffer(0, 0, 32, 32, 0, 0, client.right, client.bottom, GL_COLOR_BUFFER_BIT, GL_NEAREST);
        require(SwapBuffers(window.dc) != FALSE, "present WGL drawable");
        std::cout << "present=" << client.right << 'x' << client.bottom << '\n';
    }
    require(glGetError() == GL_NO_ERROR, "OpenGL errors");
    modules(prefix + "-" + std::to_string(cycle) + "-modules.txt");
    gl.UseProgram(0); gl.DeleteProgram(program); gl.DeleteShader(vs); gl.DeleteShader(fs);
    gl.BindFramebuffer(0x8D40, 0); gl.DeleteFramebuffers(1, &fbo); glDeleteTextures(1, &texture);
    gl.DeleteVertexArrays(1, &vao);
    require(glGetError() == GL_NO_ERROR, "OpenGL resource deletion");
    window.close();
    std::cout << "cycle=" << cycle << " passed\n";
}
} // namespace
int main(int argc, char **argv) {
    try {
        require(argc == 2, "usage: orbiter-wgl-probe <output-prefix>");
        for (int i = 0; i < 3; ++i) probe(i, argv[1]);
        std::cout << "WGL bootstrap passed\n";
        return 0;
    } catch (const std::exception &error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
