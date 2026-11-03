// Licensed under the MIT License
// Dynamic Xlib ownership checks; no link dependency keeps Xlib resident.
#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif
#include <X11/Xlib.h>
#include <X11/Xresource.h>
#include <dlfcn.h>
#include <fcntl.h>
#include <link.h>
#include <sys/stat.h>
#include <time.h>
#include <clocale>
#include <cstdlib>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>

static void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}
class Library {
    void* handle = nullptr;
    std::string path;
public:
    explicit Library(const char* name) : path(name) {
        handle = dlopen(name, RTLD_NOW | RTLD_LOCAL);
        if (!handle) throw std::runtime_error(dlerror());
        link_map* map = nullptr;
        require(dlinfo(handle, RTLD_DI_LINKMAP, &map) == 0 && map, "Loaded Xlib identity unavailable");
        std::printf("loaded_library=%s\n", map->l_name);
    }
    ~Library() { if (handle) dlclose(handle); }
    Library(const Library&) = delete;
    Library& operator=(const Library&) = delete;
    template<class T> T symbol(const char* name) const {
        auto value = reinterpret_cast<T>(dlsym(handle, name));
        require(value != nullptr, name);
        return value;
    }
    void close(bool last) {
        require(handle && dlclose(handle) == 0, "Xlib owner release failed");
        handle = nullptr;
        void* remaining = dlopen(path.c_str(), RTLD_NOW | RTLD_NOLOAD);
        const bool loaded = remaining != nullptr;
        if (remaining) dlclose(remaining);
        require(loaded != last, "Xlib unloaded before its last owner or survived its final owner");
    }
};

static void resources(const Library& library) {
    library.symbol<decltype(&XrmInitialize)>("XrmInitialize")();
    auto create = library.symbol<decltype(&XrmGetStringDatabase)>("XrmGetStringDatabase");
    auto get = library.symbol<decltype(&XrmGetResource)>("XrmGetResource");
    auto destroy = library.symbol<decltype(&XrmDestroyDatabase)>("XrmDestroyDatabase");
    for (unsigned repeat = 0; repeat < 8; ++repeat) {
        XrmDatabase db = create("Xft.dpi: 144\nOrbiter.background: blue\nOrbiter.text: orbital flight\n");
        require(db, "Resource database creation failed");
        XrmValue value{}; char* type = nullptr;
        require(get(db, "Xft.dpi", "Xft.Dpi", &type, &value) && type &&
                std::strcmp(type, "String") == 0 && value.addr &&
                std::strcmp(value.addr, "144") == 0, "Resource value changed");
        destroy(db);
    }
}

static void pool(const Library& library, unsigned worker, unsigned count) {
    auto intern = library.symbol<decltype(&XrmStringToQuark)>("XrmStringToQuark");
    auto name = library.symbol<decltype(&XrmQuarkToString)>("XrmQuarkToString");
    std::vector<XrmQuark> ids;
    for (unsigned index = 0; index < count; ++index) {
        const std::string text = "orbiter."+std::to_string(worker)+"."+std::to_string(index);
        const auto id = intern(text.c_str());
        require(id && std::strcmp(name(id), text.c_str()) == 0, "Quark value changed");
        ids.push_back(id);
    }
    // Re-read after hash-table growth and arena rollover.
    for (unsigned index = 0; index < count; ++index) {
        const std::string text = "orbiter."+std::to_string(worker)+"."+std::to_string(index);
        require(std::strcmp(name(ids[index]), text.c_str()) == 0, "Existing quark invalidated by growth");
    }
    const std::string large(20000, char('A'+worker));
    require(std::strcmp(name(intern(large.c_str())), large.c_str()) == 0, "Large permanent allocation changed");
}

static std::vector<std::string> composeMappings();

static void display(const Library& library, bool mapped, bool invalidate) {
    auto open = library.symbol<decltype(&XOpenDisplay)>("XOpenDisplay");
    auto close = library.symbol<decltype(&XCloseDisplay)>("XCloseDisplay");
    auto modifiers = library.symbol<decltype(&XSetLocaleModifiers)>("XSetLocaleModifiers");
    auto openIM = library.symbol<decltype(&XOpenIM)>("XOpenIM");
    auto closeIM = library.symbol<decltype(&XCloseIM)>("XCloseIM");
    Display* connection = open(nullptr);
    require(connection, "Owned X11 display unavailable");
    require(modifiers("@im=none"), "Local input-method modifiers unavailable");
    // Reuse the cache, including the first heap-written and later mapped forms.
    std::vector<XIM> methods;
    for (unsigned repeat = 0; repeat < 3; ++repeat) {
        XIM input = openIM(connection, nullptr, nullptr, nullptr);
        require(input, "Local input method unavailable");
        require(!composeMappings().empty() == mapped, "Expected compose heap/mapped ownership path was not exercised");
        methods.push_back(input);
        if (invalidate && repeat == 0) {
            timespec stamp[2]{};
            require(clock_gettime(CLOCK_REALTIME, &stamp[0]) == 0, "Cannot timestamp owned compose fixture");
            stamp[0].tv_sec += 60; stamp[1] = stamp[0];
            require(utimensat(AT_FDCWD, std::getenv("XCOMPOSEFILE"), stamp, 0) == 0,
                    "Cannot invalidate owned compose cache");
        }
        if (invalidate && repeat > 0) {
            bool retained = false;
            for (const auto& mapping : composeMappings()) if (mapping.find("(deleted)") != std::string::npos) retained = true;
            require(retained, "Borrowed old compose mapping was not preserved across cache replacement");
        }
    }
    for (unsigned index : {1u, 0u, 2u}) require(closeIM(methods[index]) != 0, "Input method close failed");
    require(close(connection) == 0, "Display close failed");
    resources(library); // Display close must not invalidate library-wide caches.
    std::printf("compose_mapped_while_live=%s\n", mapped ? "true" : "false");
}

static std::vector<std::string> composeMappings() {
    const char* cache = std::getenv("XCOMPOSECACHE");
    require(cache && *cache, "Owned compose cache path required");
    std::ifstream file("/proc/self/maps");
    require(bool(file), "Process maps unavailable");
    std::vector<std::string> result;
    std::string line;
    while (std::getline(file, line)) if (line.find(cache) != std::string::npos) result.push_back(line);
    return result;
}

int main(int argc, char** argv) {
    try {
        require(argc == 3, "Usage: xlib_probe absolute-library mode");
        const std::string mode = argv[2];
        require(mode == "load-only" || mode == "initialize" || mode == "resources-C" ||
                mode == "resources-UTF8" || mode == "pool" || mode == "threads" ||
                mode == "owners" || mode == "reload" || mode == "display-heap" ||
                mode == "display-mapped" || mode == "display-mixed", "Unknown Xlib test mode");
        require(std::setlocale(LC_CTYPE, mode == "resources-C" ? "C" : "C.UTF-8"), "Required test locale unavailable");
        const bool withDisplay = mode.rfind("display-", 0) == 0;
        const auto mappings = withDisplay ? composeMappings() : std::vector<std::string>{};
        const unsigned repeats = mode == "reload" ? 24 : 1;
        for (unsigned repeat = 0; repeat < repeats; ++repeat) {
            Library library(argv[1]);
            if (mode != "load-only") library.symbol<decltype(&XrmInitialize)>("XrmInitialize")();
            if (mode == "resources-C" || mode == "resources-UTF8" || mode == "reload") resources(library);
            if (mode == "pool") pool(library, 0, 6000);
            if (mode == "threads") {
                std::vector<std::thread> workers;
                for (unsigned index = 0; index < 4; ++index)
                    workers.emplace_back([&library, index] { pool(library, index, 2000); });
                for (auto& worker : workers) worker.join();
            }
            if (mode == "owners") {
                Library other(argv[1]);
                resources(library);
                library.close(false);
                resources(other);
                pool(other, 0, 3000);
                other.close(true);
            } else {
                if (withDisplay) display(library, mode != "display-heap", mode == "display-mixed");
                library.close(true);
            }
        }
        if (withDisplay) require(composeMappings() == mappings, "Compose mappings survived Xlib unload");
        std::printf("mode=%s final_owner_released=true library_unloaded=true\n", argv[2]);
        std::fflush(stdout);
        return 0;
    } catch (const std::exception& error) {
        std::fprintf(stderr, "%s\n", error.what());
        return 1;
    }
}
