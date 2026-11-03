// Observe Windows CRT dispatch without loading or modifying the simulator.
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <winver.h>
#include <intrin.h>
#include <xmmintrin.h>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

static void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

static std::string utf8(const std::wstring& value) {
    const int size = WideCharToMultiByte(CP_UTF8, WC_ERR_INVALID_CHARS,
        value.data(), static_cast<int>(value.size()), nullptr, 0, nullptr, nullptr);
    require(size > 0, "Cannot encode module path");
    std::string result(size, '\0');
    require(WideCharToMultiByte(CP_UTF8, WC_ERR_INVALID_CHARS, value.data(),
        static_cast<int>(value.size()), result.data(), size, nullptr, nullptr) == size,
        "Cannot encode module path");
    return result;
}

static std::string version(DWORD high, DWORD low) {
    return std::to_string(HIWORD(high)) + "." + std::to_string(LOWORD(high)) + "." +
        std::to_string(HIWORD(low)) + "." + std::to_string(LOWORD(low));
}

static void provider(FARPROC address) {
    HMODULE owner = nullptr;
    require(GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS |
        GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
        reinterpret_cast<LPCWSTR>(address), &owner) != 0, "Cannot identify export owner");
    std::vector<wchar_t> path(32768);
    const DWORD length = GetModuleFileNameW(owner, path.data(), static_cast<DWORD>(path.size()));
    require(length && length < path.size(), "Cannot resolve export owner path");
    DWORD ignored = 0;
    const DWORD size = GetFileVersionInfoSizeW(path.data(), &ignored);
    require(size != 0, "Missing CRT version resource");
    std::vector<char> resource(size);
    require(GetFileVersionInfoW(path.data(), 0, size, resource.data()) != 0,
        "Cannot read CRT version resource");
    VS_FIXEDFILEINFO* info = nullptr;
    UINT infoSize = 0;
    require(VerQueryValueW(resource.data(), L"\\", reinterpret_cast<void**>(&info), &infoSize) &&
        infoSize >= sizeof(*info) && info->dwSignature == 0xfeef04bd,
        "Invalid CRT version resource");
    std::cout << "{\"path\":" << std::quoted(utf8(std::wstring(path.data(), length)))
        << ",\"file_version\":" << std::quoted(version(info->dwFileVersionMS, info->dwFileVersionLS))
        << ",\"product_version\":" << std::quoted(version(info->dwProductVersionMS, info->dwProductVersionLS))
        << '}';
}

static std::uint64_t bits(double value) {
    std::uint64_t result;
    static_assert(sizeof(result) == sizeof(value));
    std::memcpy(&result, &value, sizeof(result));
    return result;
}

int wmain(int argc, wchar_t** argv) {
    try {
        require(argc == 2 || argc == 3, "Usage: probe default|sse2|fma3 [absolute CRT path]");
        const std::wstring profile(argv[1]);
        require(profile == L"default" || profile == L"sse2" || profile == L"fma3", "Unknown profile");
#ifdef _DEBUG
        const auto linked = GetModuleHandleW(L"ucrtbased.dll");
        const char* configuration = "Debug";
#else
        const auto linked = GetModuleHandleW(L"ucrtbase.dll");
        const char* configuration = "Release";
#endif
        // Each requested SDK DLL is loaded in a fresh Release process. Its
        // actual export owner is recorded; loader redirection is not hidden.
        const auto selected = argc == 3 ? LoadLibraryExW(argv[2], nullptr,
            LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR | LOAD_LIBRARY_SEARCH_SYSTEM32) : linked;
        require(selected && linked, "Cannot load requested CRT");
        const auto symbol = GetProcAddress(selected, "asin");
        const auto linkedSymbol = GetProcAddress(linked, "asin");
        const auto asinFn = reinterpret_cast<double(*)(double)>(symbol);
        const auto getFma = reinterpret_cast<int(*)()>(GetProcAddress(selected, "_get_FMA3_enable"));
        const auto setFma = reinterpret_cast<int(*)(int)>(GetProcAddress(selected, "_set_FMA3_enable"));
        require(symbol && linkedSymbol && getFma && setFma, "Required CRT exports unavailable");
        const int initial = getFma();
        if (profile != L"default") setFma(profile == L"fma3" ? 1 : 0);
        const int active = getFma();
        require(profile != L"sse2" || active == 0, "CRT did not disable FMA3");
        int cpu[4]{};
        char brand[49]{};
        __cpuid(cpu, static_cast<int>(0x80000000u));
        if (static_cast<unsigned>(cpu[0]) >= 0x80000004u) {
            for (unsigned i = 0; i != 3; ++i) {
                __cpuid(cpu, static_cast<int>(0x80000002u + i));
                std::memcpy(brand + i * 16, cpu, 16);
            }
        }
        __cpuid(cpu, 1);
        std::cout << "{\"configuration\":" << std::quoted(configuration)
            << ",\"msc_full_ver\":" << _MSC_FULL_VER
            << ",\"cpu\":" << std::quoted(brand)
            << ",\"cpuid_fma\":" << ((cpu[2] >> 12) & 1)
            << ",\"mxcsr\":" << _mm_getcsr()
            << ",\"initial_fma3\":" << initial << ",\"active_fma3\":" << active
            << ",\"linked_provider\":";
        provider(linkedSymbol);
        std::cout << ",\"exported_provider\":";
        provider(symbol);
        std::cout << "}\ninput,linked,exported\n";
        std::uint64_t input = 0;
        std::size_t count = 0;
        while (std::cin >> std::hex >> input) {
            double value;
            std::memcpy(&value, &input, sizeof(value));
            volatile double x = value;
            // /Oi- and a volatile input keep the linked call in the CRT.
            const double linkedResult = std::asin(x);
            const double exportedResult = asinFn(x);
            std::cout << std::hex << std::setfill('0') << std::setw(16) << input << ','
                << std::setw(16) << bits(linkedResult) << ',' << std::setw(16) << bits(exportedResult) << '\n';
            ++count;
        }
        require(std::cin.eof() && count > 0, "Invalid or empty input corpus");
        setFma(initial);
        require(getFma() == initial, "CRT profile restoration failed");
        require(bool(std::cout), "Cannot write probe results");
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << " (Win32 error " << GetLastError() << ")\n";
        return 1;
    }
}
