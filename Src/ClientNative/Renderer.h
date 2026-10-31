// Licensed under the MIT License.
#pragma once
#include "GlApi.h"
#include "View.h"
#include <deque>
#include <filesystem>
#include <string>
#include <vector>

namespace orbiter {
namespace client {
class Renderer {
  public:
    Renderer();
    ~Renderer();
    Renderer(const Renderer &) = delete;
    Renderer &operator=(const Renderer &) = delete;
    void Frame(const Snapshot &snapshot, const Camera &camera, bool paused, int width, int height);
    void Trail(const PhysicsTraceSample &state);
    void Screenshot(const std::filesystem::path &path, int width, int height);
    std::string Driver() const;

  private:
    struct Vertex {
        float x, y, z, r, g, b;
    };
    GlApi gl;
    GLuint program = 0, vao = 0, buffer = 0;
    GLint projection = -1;
    std::deque<Vector> trail;
    void Destroy();
    void Draw(const std::vector<Vertex> &vertices, GLenum mode, const std::array<float, 16> &matrix);
    void Check() const;
    GLuint Shader(GLenum type, const char *source);
};
} // namespace client
} // namespace orbiter
