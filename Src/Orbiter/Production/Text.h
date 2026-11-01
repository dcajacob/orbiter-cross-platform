// Licensed under the MIT License
#ifndef ORBITER_PRODUCTION_TEXT_H
#define ORBITER_PRODUCTION_TEXT_H
#include <cstddef>
namespace orbiter::production {
inline int ComparePrefix(const char* a, const char* b, std::size_t count)
{
    for (std::size_t i = 0; i < count; ++i) {
        auto lower = [](unsigned char c) { return c >= 'A' && c <= 'Z' ? c + 32 : c; };
        const int x = lower(static_cast<unsigned char>(a[i]));
        const int y = lower(static_cast<unsigned char>(b[i]));
        if (x != y || !x) return x - y;
    }
    return 0;
}

}
#endif
