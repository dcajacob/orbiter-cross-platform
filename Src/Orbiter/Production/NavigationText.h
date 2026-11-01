// Licensed under the MIT License
#ifndef ORBITER_PRODUCTION_NAVIGATION_TEXT_H
#define ORBITER_PRODUCTION_NAVIGATION_TEXT_H
#include <cstdio>
#include <cstring>
#include <stdexcept>
#include <vector>
namespace orbiter::production {
// Keep the original description-length/termination contract, including a full
// truncated buffer with no trailing NUL and return value -1. Native formatting
// uses standard C++; this does not provide operating-system API emulation.
template<class... Arguments>
int NavigationText(char* destination,int capacity,const char* format,Arguments... arguments)
{
#ifdef _WIN32
    return _snprintf(destination,capacity,format,arguments...);
#else
    if (capacity<0 || (!destination && capacity)) throw std::invalid_argument("Invalid navigation text buffer");
    std::vector<char> buffer(static_cast<std::size_t>(capacity)+1);
    const int length=std::snprintf(buffer.data(),buffer.size(),format,arguments...);
    if (length<0) return length;
    if (capacity) std::memcpy(destination,buffer.data(),length>=capacity ? capacity : length+1);
    return length>=capacity ? -1 : length;
#endif
}
}
#endif
