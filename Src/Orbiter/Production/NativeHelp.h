// Licensed under the MIT License
#pragma once
#include "ResourceResolver.h"
#include <string>
#include <vector>

namespace orbiter::production {
// Resolve only staged original books/topics, then hand a file URL to the user's
// desktop help/browser application. No command shell or network server is used.
std::string NativeHelpUrl(const ResourceResolver&, const std::string& book, const std::string& topic);
std::string NativeContextHelpUrl(const ResourceResolver&, const std::string& context, bool vessel);
void OpenNativeHelp(const std::string& url);
std::vector<std::string> PollNativeHelp();
}
