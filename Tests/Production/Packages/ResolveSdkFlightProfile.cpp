#include "../../../Utils/InstalledProfile/WindowsProfile.h"
#include <filesystem>
#include <fstream>

int wmain(int argc, wchar_t **argv)
{
    if (argc != 3) return 2;
    const std::filesystem::path profile = installed_profile::simulatorWorkingDirectory(argv[1]);
    std::ofstream output(argv[2], std::ios::binary);
    output << profile.u8string();
    return output.good() ? 0 : 1;
}
