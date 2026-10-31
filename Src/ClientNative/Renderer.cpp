// Licensed under the MIT License.
#include "Renderer.h"
#include <algorithm>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <locale>
#include <map>
#include <sstream>

namespace orbiter {
namespace client {
namespace {
constexpr GLenum TRIANGLES = 0x0004, LINES = 0x0001, LINE_STRIP = 0x0003;
constexpr GLenum ARRAY_BUFFER = 0x8892, STREAM_DRAW = 0x88E0, FLOAT = 0x1406, DEPTH_TEST = 0x0B71;
constexpr GLenum COLOR_BUFFER_BIT = 0x4000, DEPTH_BUFFER_BIT = 0x0100;
const char *vertexShader = R"GL(#version 330 core
layout(location=0) in vec3 position;
layout(location=1) in vec3 color;
uniform mat4 projection;
out vec3 tint;
void main(){gl_Position=projection*vec4(position,1.0);tint=color;}
)GL";
const char *fragmentShader = R"GL(#version 330 core
in vec3 tint;out vec4 pixel;
void main(){pixel=vec4(tint,1.0);}
)GL";
// Small built-in 5x7 bitmap alphabet; no font or visual asset installation.
const std::map<char, std::string> glyphs = {
    {'A', "01110/10001/10001/11111/10001/10001/10001"}, {'B', "11110/10001/10001/11110/10001/10001/11110"},
    {'C', "01111/10000/10000/10000/10000/10000/01111"}, {'D', "11110/10001/10001/10001/10001/10001/11110"},
    {'E', "11111/10000/10000/11110/10000/10000/11111"}, {'F', "11111/10000/10000/11110/10000/10000/10000"},
    {'G', "01111/10000/10000/10111/10001/10001/01111"}, {'H', "10001/10001/10001/11111/10001/10001/10001"},
    {'I', "11111/00100/00100/00100/00100/00100/11111"}, {'J', "00111/00010/00010/00010/10010/10010/01100"},
    {'K', "10001/10010/10100/11000/10100/10010/10001"}, {'L', "10000/10000/10000/10000/10000/10000/11111"},
    {'M', "10001/11011/10101/10101/10001/10001/10001"}, {'N', "10001/11001/10101/10011/10001/10001/10001"},
    {'O', "01110/10001/10001/10001/10001/10001/01110"}, {'P', "11110/10001/10001/11110/10000/10000/10000"},
    {'Q', "01110/10001/10001/10001/10101/10010/01101"}, {'R', "11110/10001/10001/11110/10100/10010/10001"},
    {'S', "01111/10000/10000/01110/00001/00001/11110"}, {'T', "11111/00100/00100/00100/00100/00100/00100"},
    {'U', "10001/10001/10001/10001/10001/10001/01110"}, {'V', "10001/10001/10001/10001/10001/01010/00100"},
    {'W', "10001/10001/10001/10101/10101/10101/01010"}, {'X', "10001/10001/01010/00100/01010/10001/10001"},
    {'Y', "10001/10001/01010/00100/00100/00100/00100"}, {'Z', "11111/00001/00010/00100/01000/10000/11111"},
    {'0', "01110/10001/10011/10101/11001/10001/01110"}, {'1', "00100/01100/00100/00100/00100/00100/01110"},
    {'2', "01110/10001/00001/00010/00100/01000/11111"}, {'3', "11110/00001/00001/01110/00001/00001/11110"},
    {'4', "00010/00110/01010/10010/11111/00010/00010"}, {'5', "11111/10000/10000/11110/00001/00001/11110"},
    {'6', "01110/10000/10000/11110/10001/10001/01110"}, {'7', "11111/00001/00010/00100/01000/01000/01000"},
    {'8', "01110/10001/10001/01110/10001/10001/01110"}, {'9', "01110/10001/10001/01111/00001/00001/01110"},
    {'.', "00000/00000/00000/00000/00000/00110/00110"}, {'-', "00000/00000/00000/11111/00000/00000/00000"},
    {':', "00000/00110/00110/00000/00110/00110/00000"}, {'/', "00001/00010/00010/00100/01000/01000/10000"},
    {'+', "00000/00100/00100/11111/00100/00100/00000"}};
} // namespace
GLuint Renderer::Shader(GLenum type, const char *source) {
    GLuint shader = gl.CreateShader(type);
    gl.ShaderSource(shader, 1, &source, nullptr);
    gl.CompileShader(shader);
    GLint ok = 0;
    gl.GetShaderiv(shader, 0x8B81, &ok);
    if (!ok) {
        char log[2048]{};
        gl.GetShaderInfoLog(shader, 2048, nullptr, log);
        gl.DeleteShader(shader);
        throw std::runtime_error(std::string("shader compilation: ") + log);
    }
    return shader;
}
Renderer::Renderer() {
    try {
        auto vertex = Shader(0x8B31, vertexShader);
        GLuint fragment;
        try {
            fragment = Shader(0x8B30, fragmentShader);
        } catch (...) {
            gl.DeleteShader(vertex);
            throw;
        }
        program = gl.CreateProgram();
        gl.AttachShader(program, vertex);
        gl.AttachShader(program, fragment);
        gl.LinkProgram(program);
        gl.DeleteShader(vertex);
        gl.DeleteShader(fragment);
        GLint ok = 0;
        gl.GetProgramiv(program, 0x8B82, &ok);
        if (!ok) {
            char log[2048]{};
            gl.GetProgramInfoLog(program, 2048, nullptr, log);
            throw std::runtime_error(std::string("shader link: ") + log);
        }
        projection = gl.GetUniformLocation(program, "projection");
        gl.GenVertexArrays(1, &vao);
        gl.GenBuffers(1, &buffer);
        gl.BindVertexArray(vao);
        gl.BindBuffer(ARRAY_BUFFER, buffer);
        gl.VertexAttribPointer(0, 3, FLOAT, 0, sizeof(Vertex), nullptr);
        gl.EnableVertexAttribArray(0);
        gl.VertexAttribPointer(1, 3, FLOAT, 0, sizeof(Vertex), reinterpret_cast<void *>(3 * sizeof(float)));
        gl.EnableVertexAttribArray(1);
        Check();
    } catch (...) {
        Destroy();
        throw;
    }
}
void Renderer::Destroy() {
    if (buffer)
        gl.DeleteBuffers(1, &buffer);
    if (vao)
        gl.DeleteVertexArrays(1, &vao);
    if (program)
        gl.DeleteProgram(program);
    buffer = vao = program = 0;
}
Renderer::~Renderer() {
    Destroy();
}
void Renderer::Check() const {
    auto error = gl.GetError();
    if (error)
        throw std::runtime_error("OpenGL error " + std::to_string(error));
}
std::string Renderer::Driver() const {
    return std::string(reinterpret_cast<const char *>(gl.GetString(0x1F00))) + " / " +
           reinterpret_cast<const char *>(gl.GetString(0x1F01)) + " / " +
           reinterpret_cast<const char *>(gl.GetString(0x1F02));
}
void Renderer::Draw(const std::vector<Vertex> &vertices, GLenum mode, const std::array<float, 16> &matrix) {
    if (vertices.empty())
        return;
    gl.UseProgram(program);
    gl.BindVertexArray(vao);
    gl.BindBuffer(ARRAY_BUFFER, buffer);
    gl.BufferData(ARRAY_BUFFER, GLsizeiptr(vertices.size() * sizeof(Vertex)), vertices.data(), STREAM_DRAW);
    gl.UniformMatrix4fv(projection, 1, 0, matrix.data());
    gl.DrawArrays(mode, 0, GLsizei(vertices.size()));
}
void Renderer::Trail(const PhysicsTraceSample &s) {
    if (s.step == 0)
        trail.clear();
    trail.emplace_back(s.position[0], s.position[1], s.position[2]);
    if (trail.size() > 6001)
        trail.pop_front();
}
void Renderer::Frame(const Snapshot &s, const Camera &camera, bool paused, int width, int height) {
    gl.Viewport(0, 0, width, height);
    gl.ClearColor(.012f, .021f, .045f, 1);
    gl.Clear(COLOR_BUFFER_BIT | DEPTH_BUFFER_BIT);
    gl.Enable(DEPTH_TEST);
    auto view = MakeView(camera, s, width, height);
    if (!camera.overview)
        view.nearPlane = std::max(1.0, (Position(s).length() - s.primaryRadius) * .1);
    auto matrix = view.Projection();
    std::vector<Vertex> vertices;
    auto put = [&](const Vector &world, const Vector &color) {
        const auto p = view.EyePoint(world);
        vertices.push_back(
            {float(p.x), float(p.y), float(p.z), float(color.x), float(color.y), float(color.z)});
    };
    auto sphere = [](double latitude, double longitude) {
        return Vector(std::cos(latitude) * std::cos(longitude), std::sin(latitude),
                      std::cos(latitude) * std::sin(longitude));
    };
    const Vector light = Vector(-.3, .6, -1).unit();
    for (int y = 0; y < 32; ++y)
        for (int x = 0; x < 64; ++x) {
            const double a = -Pi * .5 + Pi * y / 32, b = a + Pi / 32, c = Pi2 * x / 64, d = c + Pi2 / 64;
            Vector q[4] = {sphere(a, c), sphere(a, d), sphere(b, d), sphere(b, c)};
            const double shade = .18 + .82 * std::max(0.0, dotp(sphere((a + b) * .5, (c + d) * .5), light));
            const Vector color = Vector(.10, .39, .61) * shade;
            for (int i : {0, 1, 2, 0, 2, 3})
                put(q[i] * s.primaryRadius, color);
        }
    Draw(vertices, TRIANGLES, matrix);
    vertices.clear();
    // Sparse meridians/parallels emphasize a spherical, untextured primary.
    for (int band = -2; band <= 2; ++band)
        for (int i = 0; i < 128; ++i) {
            put(sphere(band * Pi / 6, Pi2 * i / 128) * s.primaryRadius * 1.001, Vector(.10, .26, .34));
            put(sphere(band * Pi / 6, Pi2 * (i + 1) / 128) * s.primaryRadius * 1.001, Vector(.10, .26, .34));
        }
    for (int band = 0; band < 6; ++band)
        for (int i = 0; i < 128; ++i) {
            put(sphere(-Pi * .5 + Pi * i / 128, Pi2 * band / 6) * s.primaryRadius * 1.001,
                Vector(.10, .26, .34));
            put(sphere(-Pi * .5 + Pi * (i + 1) / 128, Pi2 * band / 6) * s.primaryRadius * 1.001,
                Vector(.10, .26, .34));
        }
    Draw(vertices, LINES, matrix);
    vertices.clear();
    if (camera.overview) {
        for (const auto &p : trail)
            put(p, Vector(.25, .9, .74));
        Draw(vertices, LINE_STRIP, matrix);
        vertices.clear();
    }
    if (!camera.overview) {
        // Planet and local craft use independent depth ranges. Both positions
        // stay physical; clearing depth avoids a near/far ratio of billions.
        gl.Clear(DEPTH_BUFFER_BIT);
        view.nearPlane = .05;
        view.farPlane = 1000;
        matrix = view.Projection();
    }
    const Vector center = Position(s);
    const double scale = camera.overview ? s.primaryRadius * .018 : 1;
    auto local = [&](const Vector &p, const Vector &color) { put(center + Rotate(s, p * scale), color); };
    Vector nose(0, .25, 3), a(-1, -.65, -1.4), b(1, -.65, -1.4), top(0, .85, -1.2);
    for (const auto &face :
         std::array<std::array<Vector, 3>, 4>{{{nose, a, b}, {nose, b, top}, {nose, top, a}, {a, top, b}}}) {
        const Vector normal = Rotate(s, crossp(face[1] - face[0], face[2] - face[0])).unit();
        const double shade = .45 + .55 * std::abs(dotp(normal, light));
        for (const auto &v : face)
            local(v, Vector(.82, .87, .91) * shade);
    }
    for (double sign : {-1.0, 1.0})
        for (const auto &v : {Vector(sign, 0, -1), Vector(sign * 3.4, 0, -1), Vector(sign * 3.4, 0, .9),
                              Vector(sign, 0, -1), Vector(sign * 3.4, 0, .9), Vector(sign, 0, .9)})
            local(v, Vector(.75, .47, .12));
    Draw(vertices, TRIANGLES, matrix);
    vertices.clear();
    for (int i = 0; i < 3; ++i) {
        Vector axis;
        axis.data[i] = 4.5;
        Vector color;
        color.data[i] = .95;
        local(Vector(0, 0, 0), color);
        local(axis, color);
    }
    Draw(vertices, LINES, matrix);
    vertices.clear();

    gl.Disable(DEPTH_TEST);
    const std::array<float, 16> identity = {1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1};
    auto rectangle = [&](double x, double y, double w, double h, const Vector &color) {
        for (const auto &p : {Vector(x, y, 0), Vector(x + w, y, 0), Vector(x + w, y + h, 0), Vector(x, y, 0),
                              Vector(x + w, y + h, 0), Vector(x, y + h, 0)})
            vertices.push_back({float(2 * p.x / width - 1), float(1 - 2 * p.y / height), 0, float(color.x),
                                float(color.y), float(color.z)});
    };
    auto text = [&](const std::string &line, double x, double y, double size, const Vector &color) {
        for (char ch : line) {
            auto found = glyphs.find(ch);
            if (found != glyphs.end()) {
                int row = 0, col = 0;
                for (char bit : found->second) {
                    if (bit == '/') {
                        ++row;
                        col = 0;
                    } else {
                        if (bit == '1')
                            rectangle(x + col * size, y + row * size, size, size, color);
                        ++col;
                    }
                }
            }
            x += 6 * size;
        }
    };
    rectangle(18, 18, 370, 146, Vector(.022, .042, .071));
    rectangle(18, 18, 3, 146, Vector(.20, .86, .71));
    const Vector white(.84, .91, .94), muted(.45, .63, .70), green(.2, .86, .71);
    text("ORBITER / NATIVE", 34, 32, 2, white);
    text(camera.overview ? "OVERVIEW / VESSEL MARKER ENLARGED" : "VESSEL FOLLOW / METRES", 34, 57, 1, muted);
    std::ostringstream time;
    time.imbue(std::locale::classic());
    time << "SIM " << std::fixed << std::setprecision(0) << s.vessel.seconds << " S   "
         << (paused ? "PAUSED" : "RUNNING");
    text(time.str(), 34, 78, 2, green);
    std::ostringstream altitude;
    altitude.imbue(std::locale::classic());
    altitude << "ALT " << std::fixed << std::setprecision(2) << (center.length() - s.primaryRadius) / 1000
             << " KM   SPEED "
             << Vector(s.vessel.velocity[0], s.vessel.velocity[1], s.vessel.velocity[2]).length() / 1000
             << " KM/S";
    text(altitude.str(), 34, 105, 1, white);
    std::ostringstream mjd;
    mjd.imbue(std::locale::classic());
    mjd << "MJD " << std::fixed << std::setprecision(8) << s.vessel.mjd;
    text(mjd.str(), 34, 127, 1, muted);
    text("X RED   Y GREEN   Z BLUE", 34, 146, 1, muted);
    rectangle(18, height - 53, width - 36, 35, Vector(.022, .042, .071));
    text("SPACE PAUSE   N STEP   R RESET   TAB CAMERA   DRAG ORBIT   WHEEL ZOOM   ESC EXIT", 30, height - 41,
         1, white);
    Draw(vertices, TRIANGLES, identity);
    Check();
}
void Renderer::Screenshot(const std::filesystem::path &path, int width, int height) {
    std::vector<unsigned char> pixels(std::size_t(width) * height * 3);
    gl.PixelStorei(0x0D05, 1);
    gl.ReadPixels(0, 0, width, height, 0x1907, 0x1401, pixels.data());
    Check();
    std::ofstream file(path, std::ios::binary);
    if (!file)
        throw std::runtime_error("cannot open screenshot: " + path.string());
    file << "P6\n" << width << ' ' << height << "\n255\n";
    for (int y = height - 1; y >= 0; --y)
        file.write(reinterpret_cast<const char *>(pixels.data() + std::size_t(y) * width * 3),
                   std::streamsize(width) * 3);
    file.close();
    if (!file)
        throw std::runtime_error("cannot write screenshot");
}
} // namespace client
} // namespace orbiter
