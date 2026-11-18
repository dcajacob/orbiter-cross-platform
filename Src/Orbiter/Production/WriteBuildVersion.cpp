// Licensed under the MIT License
#include "NativeInterpreterSdk.h"
#include <fstream>
#include <iomanip>

int main(int argc, char **argv)
{
    if (argc != 2) return 1;
    std::ofstream file(argv[1]);
    file << std::setfill('0') << std::setw(6) << oapiGetOrbiterVersion() << '\n';
    file.close();
    return file ? 0 : 1;
}
