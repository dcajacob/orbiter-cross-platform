// Licensed under the MIT License
#include "VesselCoreSupport.h"
#include "SurfaceServices.h"
#include <cstdarg>
#include <cstdio>
#include <stdexcept>
#include <vector>
namespace orbiter::production {
void VesselLog(const char* format,...)
{
    va_list arguments,copy;
    va_start(arguments,format);
    va_copy(copy,arguments);
    const int size=std::vsnprintf(nullptr,0,format,copy);
    va_end(copy);
    if(size<0) {va_end(arguments);throw std::runtime_error("Cannot format vessel diagnostic");}
    std::vector<char> message(static_cast<std::size_t>(size)+1);
    std::vsnprintf(message.data(),message.size(),format,arguments);
    va_end(arguments);
    GetSurfaceServices().Log(message.data());
}
}
