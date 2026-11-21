// Licensed under the MIT License
#pragma once
#include <cstdio>
#include <string>
#ifdef _WIN32
#include <filesystem>
#include <stdexcept>
inline bool RendererResolveFilePath(const std::string& name, std::string& resolved)
{
    std::error_code error;
    if (!std::filesystem::is_regular_file(name, error)) return false;
    resolved = name;
    return true;
}
inline std::string RendererFilePath(const std::string& name)
{
    std::string resolved;
    if (RendererResolveFilePath(name, resolved)) return resolved;
    throw std::runtime_error("Required renderer asset is missing: " + name);
}
inline FILE* RendererOpenFile(const char* name,const char* mode) {return std::fopen(name,mode);}
#else
bool RendererResolveFilePath(const std::string& name,std::string& resolved);
std::string RendererFilePath(const std::string& name);
FILE* RendererOpenFile(const char* name,const char* mode);
#endif
