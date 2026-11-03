// Load and completely unload the graphics dependency, as the native client does.
#include <dlfcn.h>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <sstream>
#include <stdexcept>
#include <string>

static unsigned long long executableMappings() {
    std::ifstream maps("/proc/self/maps");
    if (!maps) throw std::runtime_error("Cannot read process mappings");
    unsigned long long total = 0;
    std::string line;
    while (std::getline(maps, line)) {
        std::istringstream row(line);
        std::string range, permissions, offset, device, inode, name;
        if (!(row >> range >> permissions >> offset >> device >> inode))
            throw std::runtime_error("Invalid process mapping");
        if (permissions == "rwxp" && !(row >> name)) {
            const auto separator = range.find('-');
            total += std::stoull(range.substr(separator + 1), nullptr, 16) -
                     std::stoull(range.substr(0, separator), nullptr, 16);
        }
    }
    return total;
}

int main(int argc, char** argv) {
    if (argc != 3 || (std::strcmp(argv[2], "mipmap") && std::strcmp(argv[2], "no-mipmap"))) {
        std::fprintf(stderr, "Usage: driver_lifetime absolute-fixture.so mipmap|no-mipmap\n");
        return 2;
    }
    const auto before = executableMappings();
    void* library = dlopen(argv[1], RTLD_NOW | RTLD_LOCAL);
    if (!library) {std::fprintf(stderr, "%s\n", dlerror()); return 3;}
    auto run = reinterpret_cast<int(*)(bool)>(dlsym(library, "run"));
    if (!run) {std::fprintf(stderr, "%s\n", dlerror()); dlclose(library); return 4;}
    const int result = run(std::strcmp(argv[2], "mipmap") == 0);
    if (dlclose(library) != 0) {std::fprintf(stderr, "%s\n", dlerror()); return 5;}
    const auto after = executableMappings();
    std::printf("anonymous_rwx_bytes_before=%llu\nanonymous_rwx_bytes_after=%llu\n", before, after);
    std::fflush(stdout);
    if (after != before) {
        std::fprintf(stderr, "Executable mappings survived graphics-module unload\n");
        return 6;
    }
    return result;
}
