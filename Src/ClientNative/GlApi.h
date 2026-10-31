// Licensed under the MIT License.
#pragma once
#include <GLFW/glfw3.h>
#include <cstddef>
#include <stdexcept>
#include <string>

namespace orbiter {
namespace client {
// The OpenGL 3.3 entry points used by this client. Resolve through GLFW on
// every platform, including Windows' legacy system OpenGL library. These are
// graphics ABI declarations, never simulation/platform emulation.
#ifdef _WIN32
#define ORBITER_GL_CALL __stdcall
#else
#define ORBITER_GL_CALL
#endif
using GLenum = unsigned int;
using GLuint = unsigned int;
using GLint = int;
using GLsizei = int;
using GLboolean = unsigned char;
using GLbitfield = unsigned int;
using GLfloat = float;
using GLsizeiptr = std::ptrdiff_t;
#define ORBITER_GL_FUNCTIONS(F)                                                                              \
    F(void, GenVertexArrays, (GLsizei, GLuint *))                                                            \
    F(void, BindVertexArray, (GLuint))                                                                       \
    F(void, DeleteVertexArrays, (GLsizei, const GLuint *))                                                   \
    F(void, GenBuffers, (GLsizei, GLuint *))                                                                 \
    F(void, BindBuffer, (GLenum, GLuint))                                                                    \
    F(void, BufferData, (GLenum, GLsizeiptr, const void *, GLenum))                                          \
    F(void, DeleteBuffers, (GLsizei, const GLuint *))                                                        \
    F(void, VertexAttribPointer, (GLuint, GLint, GLenum, GLboolean, GLsizei, const void *))                  \
    F(void, EnableVertexAttribArray, (GLuint))                                                               \
    F(GLuint, CreateShader, (GLenum))                                                                        \
    F(void, ShaderSource, (GLuint, GLsizei, const char *const *, const GLint *))                             \
    F(void, CompileShader, (GLuint))                                                                         \
    F(void, GetShaderiv, (GLuint, GLenum, GLint *))                                                          \
    F(void, GetShaderInfoLog, (GLuint, GLsizei, GLsizei *, char *))                                          \
    F(void, DeleteShader, (GLuint))                                                                          \
    F(GLuint, CreateProgram, ())                                                                             \
    F(void, AttachShader, (GLuint, GLuint))                                                                  \
    F(void, LinkProgram, (GLuint))                                                                           \
    F(void, GetProgramiv, (GLuint, GLenum, GLint *))                                                         \
    F(void, GetProgramInfoLog, (GLuint, GLsizei, GLsizei *, char *))                                         \
    F(void, DeleteProgram, (GLuint))                                                                         \
    F(void, UseProgram, (GLuint))                                                                            \
    F(GLint, GetUniformLocation, (GLuint, const char *))                                                     \
    F(void, UniformMatrix4fv, (GLint, GLsizei, GLboolean, const GLfloat *))                                  \
    F(void, DrawArrays, (GLenum, GLint, GLsizei))                                                            \
    F(void, Enable, (GLenum))                                                                                \
    F(void, Disable, (GLenum))                                                                               \
    F(void, ClearColor, (GLfloat, GLfloat, GLfloat, GLfloat))                                                \
    F(void, Clear, (GLbitfield))                                                                             \
    F(void, Viewport, (GLint, GLint, GLsizei, GLsizei))                                                      \
    F(GLenum, GetError, ())                                                                                  \
    F(const unsigned char *, GetString, (GLenum))                                                            \
    F(void, ReadPixels, (GLint, GLint, GLsizei, GLsizei, GLenum, GLenum, void *))                            \
    F(void, PixelStorei, (GLenum, GLint))
struct GlApi {
#define DECLARE(ret, name, args)                                                                             \
    using name##Proc = ret(ORBITER_GL_CALL *) args;                                                          \
    name##Proc name = nullptr;
    ORBITER_GL_FUNCTIONS(DECLARE)
#undef DECLARE
    GlApi() {
#define LOAD(ret, name, args)                                                                                \
    name = reinterpret_cast<name##Proc>(glfwGetProcAddress("gl" #name));                                     \
    if (!name)                                                                                               \
        throw std::runtime_error("missing OpenGL entry point: gl" #name);
        ORBITER_GL_FUNCTIONS(LOAD)
#undef LOAD
    }
};
#undef ORBITER_GL_FUNCTIONS
#undef ORBITER_GL_CALL
} // namespace client
} // namespace orbiter
