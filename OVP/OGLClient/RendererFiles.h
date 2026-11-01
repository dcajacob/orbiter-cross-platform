// Licensed under the MIT License
#pragma once
#include <cstdio>
#include <string>
#ifdef _WIN32
inline bool RendererResolveFilePath(const std::string& name,std::string& resolved) {resolved=name;return true;}
inline std::string RendererFilePath(const std::string& name) {return name;}
inline FILE* RendererOpenFile(const char* name,const char* mode) {return std::fopen(name,mode);}
#else
bool RendererResolveFilePath(const std::string& name,std::string& resolved);
std::string RendererFilePath(const std::string& name);
FILE* RendererOpenFile(const char* name,const char* mode);
#endif
