// Licensed under the MIT License
#pragma once
#include <string>

namespace installed_profile {
std::wstring simulatorWorkingDirectory(const std::wstring &exe);
void enterStockWorkingDirectory();
}
