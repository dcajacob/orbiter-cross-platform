// Licensed under the MIT License
#include "WindowsProfile.h"
#include <windows.h>
#include <shlobj.h>
#include <winioctl.h>
#include <filesystem>
#include <fstream>
#include <sstream>
#include <vector>
#include <system_error>
#include <cstdint>
#include <cwctype>
#include <cstring>
#pragma comment(lib, "shell32.lib")
#pragma comment(lib, "ole32.lib")

namespace installed_profile {
namespace fs = std::filesystem;

static void winError(const char *what) {
    throw std::system_error(static_cast<int>(GetLastError()), std::system_category(), what);
}

// A directory junction can be created by a standard account on NTFS. It lets
// the classic engine continue using its relative paths for shared stock assets.
static void junction(const fs::path &link, const fs::path &target) {
    if (fs::exists(link)) {
        if (!fs::equivalent(link, target)) throw std::runtime_error("Unexpected shared asset location");
        return;
    }
    fs::create_directory(link);
    HANDLE h = CreateFileW(link.c_str(), GENERIC_WRITE, 0, nullptr, OPEN_EXISTING,
                           FILE_FLAG_OPEN_REPARSE_POINT | FILE_FLAG_BACKUP_SEMANTICS, nullptr);
    if (h == INVALID_HANDLE_VALUE) winError("Open asset junction");
    const std::wstring name = target.wstring();
    std::wstring subst;
    if (name.rfind(L"\\\\?\\", 0) == 0) subst = L"\\??\\" + name.substr(4);
    else if (name.rfind(L"\\\\", 0) == 0) subst = L"\\??\\UNC\\" + name.substr(2);
    else subst = L"\\??\\" + name;
    struct Header { DWORD tag; WORD size, reserved, substituteOffset, substituteBytes, printOffset, printBytes; };
    const size_t size = sizeof(Header) + (subst.size() + name.size() + 2) * sizeof(wchar_t);
    if (size > MAXIMUM_REPARSE_DATA_BUFFER_SIZE) { CloseHandle(h); throw std::runtime_error("Asset path too long"); }
    std::vector<unsigned char> bytes(size);
    Header fields{IO_REPARSE_TAG_MOUNT_POINT, WORD(size-8), 0, 0, WORD(subst.size()*2),
                  WORD((subst.size()+1)*2), WORD(name.size()*2)};
    memcpy(bytes.data(), &fields, sizeof(fields));
    memcpy(bytes.data()+sizeof(fields), subst.c_str(), (subst.size()+1)*2);
    memcpy(bytes.data()+sizeof(fields)+(subst.size()+1)*2, name.c_str(), (name.size()+1)*2);
    DWORD count;
    BOOL ok = DeviceIoControl(h, FSCTL_SET_REPARSE_POINT, bytes.data(), DWORD(size), nullptr, 0, &count, nullptr);
    DWORD error = GetLastError();
    CloseHandle(h);
    if (!ok) { fs::remove(link); throw std::system_error(error, std::system_category(), "Create asset junction"); }
}

static void seed(const fs::path &src, const fs::path &dest) {
    if (fs::is_directory(src)) {
        fs::create_directories(dest);
        for (const auto &item : fs::directory_iterator(src)) seed(item.path(), dest/item.path().filename());
    } else if (fs::copy_file(src, dest, fs::copy_options::skip_existing)) {
        fs::permissions(dest, fs::perms::owner_write, fs::perm_options::add);
    }
}

static bool isStockInstall(const fs::path &runtime) {
    return fs::is_regular_file(runtime/L"runtime.json") &&
           fs::is_regular_file(runtime.parent_path()/L"stock-data-receipt.json");
}

static fs::path workingDirectory(const fs::path &exe) {
    const fs::path runtime = fs::canonical(exe).parent_path();
    if (!isStockInstall(runtime)) return runtime;
    PWSTR base = nullptr;
    if (FAILED(SHGetKnownFolderPath(FOLDERID_LocalAppData, 0, nullptr, &base)))
        throw std::runtime_error("Cannot locate the user's LocalAppData folder");
    fs::path local(base);
    CoTaskMemFree(base);
    uint64_t identity = 14695981039346656037ULL;
    for (wchar_t c : runtime.wstring()) { identity ^= std::towlower(c); identity *= 1099511628211ULL; }
    std::wostringstream id;
    id << std::hex << identity;
    const fs::path state = local/L"Orbiter"/L"Installations"/id.str();
    fs::create_directories(state);
    // Lock only initialization. The kernel releases the file handle on exit.
    HANDLE lock = INVALID_HANDLE_VALUE;
    for (int attempt=0; attempt<300; ++attempt) {
        lock = CreateFileW((state/L"setup.lock").c_str(), GENERIC_WRITE, 0, nullptr, OPEN_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr);
        if (lock != INVALID_HANDLE_VALUE) break;
        if (GetLastError()!=ERROR_SHARING_VIOLATION) winError("Open user profile lock");
        Sleep(100);
    }
    if (lock==INVALID_HANDLE_VALUE) throw std::runtime_error("Timed out preparing the user's Orbiter files");
    struct Guard { HANDLE h; ~Guard() { CloseHandle(h); } } guard{lock};
    const auto revision = std::to_string(fs::last_write_time(runtime/L"runtime.json").time_since_epoch().count());
    const auto marker = state/L"installed-version";
    std::string previous;
    { std::ifstream input(marker); std::getline(input, previous); }
    if (previous == revision) return state;
    for (const auto &entry : fs::directory_iterator(runtime)) {
        const auto name = entry.path().filename();
        const auto dest = state/name;
        if (entry.is_directory()) {
            if (name==L"Scenarios" || name==L"Config" || name==L"Flights" || name==L"Images" || name==L"XRSound")
                seed(entry.path(), dest);
            else junction(dest, entry.path());
        } else if (_wcsicmp(name.extension().c_str(), L".cfg")==0 || _wcsicmp(name.extension().c_str(), L".ini")==0) {
            seed(entry.path(), dest);
        }
    }
    fs::create_directories(state/L"Scenarios"/L"Quicksave");
    std::ofstream done(marker, std::ios::trunc);
    done << revision;
    done.close();
    if (!done) throw std::runtime_error("Cannot record completed Orbiter profile setup");
    return state;
}
std::wstring simulatorWorkingDirectory(const std::wstring &exe) {
    return workingDirectory(exe).wstring();
}

void enterStockWorkingDirectory() {
    wchar_t exe[32768];
    const DWORD length = GetModuleFileNameW(nullptr, exe, 32768);
    if (!length || length == 32768) throw std::runtime_error("Cannot locate Orbiter.exe");
    if (isStockInstall(fs::path(exe).parent_path())) fs::current_path(workingDirectory(exe));
}
}
