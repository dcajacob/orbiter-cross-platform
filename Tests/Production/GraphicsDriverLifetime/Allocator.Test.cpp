// Exercise Mesa's actual allocator objects, including overlapping live code.
// This executable is specific to the x86-64 rtasm backend used by llvmpipe.
#include <atomic>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>

extern "C" void* rtasm_exec_malloc(std::size_t);
extern "C" void rtasm_exec_free(void*);

static void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

static std::uint64_t mappings() {
    std::ifstream file("/proc/self/maps");
    require(bool(file), "Cannot inspect executable mappings");
    std::string line;
    std::uint64_t total = 0;
    while (std::getline(file, line)) {
        std::istringstream row(line);
        std::string range, permissions, offset, device, inode, name;
        require(bool(row >> range >> permissions >> offset >> device >> inode), "Invalid mapping");
        if (permissions == "rwxp" && !(row >> name)) {
            const auto split = range.find('-');
            total += std::stoull(range.substr(split + 1), nullptr, 16) -
                     std::stoull(range.substr(0, split), nullptr, 16);
        }
    }
    return total;
}

static void* code(std::uint32_t value) {
    auto* memory = static_cast<unsigned char*>(rtasm_exec_malloc(32));
    require(memory != nullptr, "Executable allocation failed");
    // ENDBR64; MOV EAX, imm32; RET. No external calls or mutable shared data.
    const unsigned char instructions[] = {0xf3, 0x0f, 0x1e, 0xfa, 0xb8, 0, 0, 0, 0, 0xc3};
    std::memcpy(memory, instructions, sizeof(instructions));
    std::memcpy(memory + 5, &value, sizeof(value));
    __builtin___clear_cache(reinterpret_cast<char*>(memory), reinterpret_cast<char*>(memory + sizeof(instructions)));
    return memory;
}

static std::uint32_t call(void* memory) {
    return reinterpret_cast<std::uint32_t(*)()>(memory)();
}

int main() {
    try {
        const auto initial = mappings();
        void* first = code(0x12345678);
        void* second = code(0x34567890);
        require(call(first) == 0x12345678 && call(second) == 0x34567890, "Generated code differs");
        rtasm_exec_free(first);
        require(call(second) == 0x34567890, "Freeing one owner invalidated another's code");
        rtasm_exec_free(second);
        require(mappings() == initial, "The final free retained an executable heap");

        require(rtasm_exec_malloc(11 * 1024 * 1024) == nullptr, "Oversized request unexpectedly succeeded");
        require(mappings() == initial, "Failed allocation retained an empty executable heap");

        std::atomic<bool> failed{false};
        std::vector<std::thread> threads;
        for (std::uint32_t thread = 0; thread < 4; ++thread) {
            threads.emplace_back([thread, &failed] {
                try {
                    for (std::uint32_t i = 0; i < 500; ++i) {
                        const auto value = 1000 * thread + i;
                        void* a = code(value);
                        void* b = code(value + 1);
                        require(call(a) == value, "Concurrent code corruption");
                        rtasm_exec_free(a);
                        require(call(b) == value + 1, "Concurrent free invalidated live code");
                        rtasm_exec_free(b);
                    }
                } catch (...) {failed = true;}
            });
        }
        for (auto& thread : threads) thread.join();
        require(!failed, "Concurrent allocation/free test failed");
        require(mappings() == initial, "Concurrent teardown retained executable mappings");
        std::puts("Overlapping code owners, allocation failure and 4,000 concurrent allocations passed");
        return 0;
    } catch (const std::exception& error) {
        std::fprintf(stderr, "%s\n", error.what());
        return 1;
    }
}
