// Licensed under the MIT License.
#include "Renderer.h"
#include <chrono>
#include <exception>
#include <fstream>
#include <iostream>
#include <limits>
#include <locale>
#include <map>
#include <memory>
#include <sstream>

using namespace orbiter;
using namespace orbiter::client;
namespace {
double Number(const std::string &text) {
    std::istringstream s(text);
    s.imbue(std::locale::classic());
    double v;
    if (!(s >> v) || !std::isfinite(v))
        throw std::runtime_error("invalid finite number: " + text);
    s >> std::ws;
    if (!s.eof())
        throw std::runtime_error("invalid number suffix: " + text);
    return v;
}
std::size_t Count(const std::string &text) {
    if (text.empty() || text.find_first_not_of("0123456789") != std::string::npos)
        throw std::runtime_error("expected positive integer");
    auto v = std::stoull(text);
    if (!v || v > std::numeric_limits<std::size_t>::max())
        throw std::runtime_error("step count outside supported range");
    return std::size_t(v);
}
std::string Json(const std::string &text) {
    std::string out = "\"";
    for (unsigned char c : text) {
        if (c == '"' || c == '\\')
            out += '\\';
        if (c < 32)
            out += ' ';
        else
            out += char(c);
    }
    return out + '"';
}
bool SamePath(const std::filesystem::path &a, const std::filesystem::path &b) {
    if (std::filesystem::absolute(a).lexically_normal() == std::filesystem::absolute(b).lexically_normal())
        return true;
    return std::filesystem::exists(a) && std::filesystem::exists(b) && std::filesystem::equivalent(a, b);
}
struct Trace {
    std::filesystem::path path;
    PhysicsTrace writer;
    PhysicsTraceSample last{};
    std::size_t written = 0, segment = 0;
    const Controller &controller;
    std::vector<std::filesystem::path> protectedPaths;
    Trace(std::filesystem::path file, const Controller &c, std::vector<std::filesystem::path> protectedFiles)
        : path(std::move(file)), controller(c), protectedPaths(std::move(protectedFiles)) {}
    void End() {
        if (writer.IsOpen()) {
            if (last.step != written)
                writer.Write(last);
            writer.Close();
        }
    }
    void Observe(const PhysicsTraceSample &s) {
        if (path.empty())
            return;
        if (s.step == 0) {
            End();
            auto file = path;
            if (segment)
                file = path.parent_path() / (path.stem().string() + ".run-" + std::to_string(segment + 1) +
                                             path.extension().string());
            if (controller.IsInputFile(file))
                throw std::runtime_error("trace would overwrite a simulation input");
            for (const auto &protectedFile : protectedPaths)
                if (SamePath(file, protectedFile))
                    throw std::runtime_error("trace segment would overwrite another input/output");
            writer.Open(file.string());
            ++segment;
        }
        last = s;
        if (s.step % 10 == 0 || controller.Finished()) {
            writer.Write(s);
            written = s.step;
        }
    }
};
struct Runtime {
    ~Runtime() {
        glfwTerminate();
    }
};
struct App {
    Controller &controller;
    Camera camera;
    GLFWwindow *window;
    FrameClock clock;
    bool dragging = false;
    double x = 0, y = 0;
    std::exception_ptr error;
    ~App() {
        glfwSetKeyCallback(window, nullptr);
        glfwSetMouseButtonCallback(window, nullptr);
        glfwSetCursorPosCallback(window, nullptr);
        glfwSetScrollCallback(window, nullptr);
        glfwSetWindowUserPointer(window, nullptr);
    }
    void Command(const std::string &name, const std::vector<double> &args = {}) {
        auto arity = [&](std::size_t n) {
            if (args.size() != n)
                throw std::runtime_error("wrong command arguments: " + name);
        };
        if (name == "pause") {
            arity(0);
            controller.Pause(true);
            clock.Restart();
        } else if (name == "resume") {
            arity(0);
            controller.Pause(false);
            clock.Restart();
        } else if (name == "toggle") {
            arity(0);
            controller.Pause(!controller.Paused());
            clock.Restart();
        } else if (name == "step") {
            arity(0);
            controller.SingleStep();
        } else if (name == "reset") {
            arity(0);
            controller.Reset();
            clock.Restart();
        } else if (name == "camera") {
            arity(0);
            camera.overview = !camera.overview;
            camera.zoom = 1;
        } else if (name == "orbit") {
            arity(2);
            camera.Orbit(args[0], args[1]);
        } else if (name == "zoom") {
            arity(1);
            camera.Zoom(args[0]);
        } else if (name == "resize") {
            arity(2);
            if (args[0] < 640 || args[1] < 360 || args[0] > 4096 || args[1] > 4096)
                throw std::runtime_error("resize outside supported range");
            glfwSetWindowSize(window, int(args[0]), int(args[1]));
        } else if (name == "exit") {
            arity(0);
            glfwSetWindowShouldClose(window, 1);
        } else
            throw std::runtime_error("unsupported input command: " + name);
    }
    template <class F> static void Guard(GLFWwindow *w, F call) noexcept {
        auto &app = *static_cast<App *>(glfwGetWindowUserPointer(w));
        try {
            call(app);
        } catch (...) {
            app.error = std::current_exception();
            glfwSetWindowShouldClose(w, 1);
        }
    }
};
struct Event {
    std::size_t frame;
    std::string name;
    std::vector<double> args;
};
std::vector<Event> Script(const std::filesystem::path &path) {
    if (path.empty())
        return {};
    std::ifstream file(path);
    if (!file)
        throw std::runtime_error("cannot open input script");
    std::vector<Event> result;
    std::size_t lineNumber = 0;
    for (std::string line; std::getline(file, line);) {
        ++lineNumber;
        auto comment = line.find('#');
        if (comment != std::string::npos)
            line.resize(comment);
        std::istringstream s(line);
        s.imbue(std::locale::classic());
        std::string frame, name;
        if (!(s >> frame))
            continue;
        if (!(s >> name))
            throw std::runtime_error("missing script command");
        if (frame.find_first_not_of("0123456789") != std::string::npos)
            throw std::runtime_error("invalid script frame");
        auto number = std::stoull(frame);
        if (number > 100000)
            throw std::runtime_error("script frame exceeds limit");
        Event event{std::size_t(number), name, {}};
        if (!result.empty() && event.frame < result.back().frame)
            throw std::runtime_error("script frames must be ordered");
        for (std::string value; s >> value;)
            event.args.push_back(Number(value));
        result.push_back(std::move(event));
    }
    if (!file.eof())
        throw std::runtime_error("cannot read input script");
    return result;
}
} // namespace
int main(int argc, char **argv) {
    try {
        std::map<std::string, std::string> options;
        bool smoke = false, hidden = false, help = false;
        for (int i = 1; i < argc; ++i) {
            std::string key = argv[i], value;
            if (key == "--help") {
                help = true;
                continue;
            }
            if (key == "--smoke-test") {
                if (smoke)
                    throw std::runtime_error("duplicate smoke option");
                smoke = true;
                continue;
            }
            if (key == "--hidden") {
                if (hidden)
                    throw std::runtime_error("duplicate hidden option");
                hidden = true;
                continue;
            }
            auto eq = key.find('=');
            if (eq != std::string::npos) {
                value = key.substr(eq + 1);
                key.resize(eq);
            } else {
                if (++i == argc)
                    throw std::runtime_error("missing option value: " + key);
                value = argv[i];
            }
            if (key != "--scenario" && key != "--fixed-step" && key != "--steps" && key != "--trace" &&
                key != "--screenshot" && key != "--report" && key != "--backend" && key != "--camera" &&
                key != "--input-script")
                throw std::runtime_error("unknown option: " + key);
            if (value.empty() || !options.emplace(key, value).second)
                throw std::runtime_error("empty or duplicate option: " + key);
        }
        if (help) {
            std::cout << "orbiter-native --scenario <path> [--fixed-step 1] [--steps N] [--trace <csv>]\n"
                         "  --backend auto|x11|wayland  --camera overview|follow\n"
                         "  --smoke-test [--hidden] [--input-script <path>] [--screenshot <ppm>] [--report "
                         "<json>]\n"
                         "Controls: Space pause/resume, N single step while paused, R reset, Tab camera, "
                         "drag orbit, wheel zoom, Esc exit.\n";
            return 0;
        }
        if (!options.count("--scenario"))
            throw std::runtime_error("--scenario is required");
        if ((hidden || options.count("--input-script")) && !smoke)
            throw std::runtime_error("hidden/script mode requires --smoke-test");
        const double step = options.count("--fixed-step") ? Number(options.at("--fixed-step")) : 1;
        const std::size_t limit =
            options.count("--steps") ? Count(options.at("--steps")) : (smoke ? 6000 : 0);
        const std::string backend = options.count("--backend") ? options.at("--backend") : "auto";
        if (backend != "auto" && backend != "x11" && backend != "wayland")
            throw std::runtime_error("invalid window backend");
        const std::string camera = options.count("--camera") ? options.at("--camera") : "overview";
        if (camera != "overview" && camera != "follow")
            throw std::runtime_error("invalid camera");
        Controller controller(options.at("--scenario"), step, limit);
        std::vector<std::filesystem::path> outputs;
        for (const char *key : {"--trace", "--screenshot", "--report"})
            if (options.count(key)) {
                auto path = std::filesystem::path(options.at(key));
                if (controller.IsInputFile(path))
                    throw std::runtime_error("output would overwrite simulation input");
                if (options.count("--input-script") && SamePath(path, options.at("--input-script")))
                    throw std::runtime_error("output would overwrite input script");
                for (const auto &other : outputs)
                    if (SamePath(path, other))
                        throw std::runtime_error("output paths must differ");
                outputs.push_back(path);
            }
        auto events = Script(options.count("--input-script") ? options.at("--input-script") : "");
        glfwSetErrorCallback([](int, const char *text) { std::cerr << "GLFW: " << text << '\n'; });
        Runtime runtime;
        if (backend != "auto")
            glfwInitHint(GLFW_PLATFORM, backend == "x11" ? GLFW_PLATFORM_X11 : GLFW_PLATFORM_WAYLAND);
        if (!glfwInit())
            throw std::runtime_error("cannot initialize native window backend");
        glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR, 3);
        glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR, 3);
        glfwWindowHint(GLFW_OPENGL_PROFILE, GLFW_OPENGL_CORE_PROFILE);
        glfwWindowHint(GLFW_OPENGL_FORWARD_COMPAT, GLFW_TRUE);
        glfwWindowHint(GLFW_VISIBLE, hidden ? GLFW_FALSE : GLFW_TRUE);
        std::unique_ptr<GLFWwindow, decltype(&glfwDestroyWindow)> window(
            glfwCreateWindow(1280, 800, "Orbiter / Native", nullptr, nullptr), glfwDestroyWindow);
        if (!window)
            throw std::runtime_error("cannot create OpenGL 3.3 core window");
        glfwSetWindowSizeLimits(window.get(), 640, 360, 4096, 4096);
        glfwMakeContextCurrent(window.get());
        glfwSwapInterval(smoke ? 0 : 1);
        Renderer renderer;
        App app{controller, Camera{}, window.get()};
        app.camera.overview = camera == "overview";
        std::vector<std::filesystem::path> protectedFiles;
        for (const char *key : {"--screenshot", "--report", "--input-script"})
            if (options.count(key))
                protectedFiles.emplace_back(options.at(key));
        Trace trace(options.count("--trace") ? options.at("--trace") : "", controller,
                    std::move(protectedFiles));
        controller.Observe([&](const auto &s) {
            trace.Observe(s);
            renderer.Trail(s);
        });
        glfwSetWindowUserPointer(window.get(), &app);
        glfwSetKeyCallback(window.get(), [](GLFWwindow *w, int key, int, int action, int) {
            if (action != GLFW_PRESS)
                return;
            App::Guard(w, [&](App &a) {
                switch (key) {
                case GLFW_KEY_SPACE:
                    a.Command("toggle");
                    break;
                case GLFW_KEY_N:
                    a.Command("step");
                    break;
                case GLFW_KEY_R:
                    a.Command("reset");
                    break;
                case GLFW_KEY_TAB:
                    a.Command("camera");
                    break;
                case GLFW_KEY_ESCAPE:
                    a.Command("exit");
                    break;
                }
            });
        });
        glfwSetMouseButtonCallback(window.get(), [](GLFWwindow *w, int button, int action, int) {
            if (button == GLFW_MOUSE_BUTTON_LEFT)
                App::Guard(w, [&](App &a) {
                    a.dragging = action == GLFW_PRESS;
                    glfwGetCursorPos(w, &a.x, &a.y);
                });
        });
        glfwSetCursorPosCallback(window.get(), [](GLFWwindow *w, double x, double y) {
            App::Guard(w, [&](App &a) {
                if (a.dragging)
                    a.Command("orbit", {(x - a.x) * .005, (y - a.y) * .005});
                a.x = x;
                a.y = y;
            });
        });
        glfwSetScrollCallback(window.get(), [](GLFWwindow *w, double, double y) {
            App::Guard(w, [&](App &a) { a.Command("zoom", {y}); });
        });
        const auto platform = glfwGetPlatform();
        const std::string platformName = platform == GLFW_PLATFORM_X11       ? "x11"
                                         : platform == GLFW_PLATFORM_WAYLAND ? "wayland"
                                                                             : "win32";
        std::cout << "Native backend: " << platformName << "\nOpenGL: " << renderer.Driver() << '\n';
        std::size_t frames = 0, nextEvent = 0;
        int width = 0, height = 0;
        do {
            glfwPollEvents();
            if (app.error)
                std::rethrow_exception(app.error);
            while (nextEvent < events.size() && events[nextEvent].frame == frames) {
                app.Command(events[nextEvent].name, events[nextEvent].args);
                ++nextEvent;
            }
            const auto elapsed = app.clock.Elapsed(std::chrono::steady_clock::now());
            controller.Advance(smoke ? std::chrono::seconds(100) : elapsed, smoke ? 100 : 8);
            glfwGetFramebufferSize(window.get(), &width, &height);
            if (width > 0 && height > 0) {
                renderer.Frame(controller.Display(), app.camera, controller.Paused(), width, height);
                if ((controller.Finished() || glfwWindowShouldClose(window.get())) &&
                    options.count("--screenshot"))
                    renderer.Screenshot(options.at("--screenshot"), width, height);
                glfwSwapBuffers(window.get());
            }
            if (controller.Finished() && (width <= 0 || height <= 0))
                throw std::runtime_error("completed run has no renderable framebuffer");
            ++frames;
            if (smoke && frames > 100000)
                throw std::runtime_error("smoke test failed to finish");
            if (!smoke && (width <= 0 || height <= 0))
                glfwWaitEventsTimeout(.05);
        } while (!controller.Finished() && !glfwWindowShouldClose(window.get()));
        if (app.error)
            std::rethrow_exception(app.error);
        trace.End();
        if (nextEvent != events.size())
            throw std::runtime_error("input script contains unexecuted events");
        if (smoke && !controller.Finished())
            throw std::runtime_error("smoke test exited before requested step");
        if (options.count("--report")) {
            std::ofstream file(options.at("--report"));
            file.imbue(std::locale::classic());
            file << "{\n  \"status\": \"passed\",\n  \"backend\": " << Json(platformName)
                 << ",\n  \"driver\": " << Json(renderer.Driver())
                 << ",\n  \"steps\": " << controller.Current().vessel.step << ",\n  \"frames\": " << frames
                 << ",\n  \"script_events\": " << nextEvent << ",\n  \"width\": " << width
                 << ",\n  \"height\": " << height << ",\n  \"gl_error\": 0\n}\n";
            file.close();
            if (!file)
                throw std::runtime_error("cannot write client report");
        }
        std::cout << "Completed " << controller.Current().vessel.step << " fixed steps in " << frames
                  << " rendered frames.\n";
        return 0;
    } catch (const std::exception &e) {
        std::cerr << "orbiter-native: " << e.what() << '\n';
        return 1;
    }
}
