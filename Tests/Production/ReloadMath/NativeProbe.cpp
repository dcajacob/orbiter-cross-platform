// Licensed under the MIT License
// Diagnostic executable linked to a retained package's actual private math archive.
#include "Runtime.h"
#include <cfenv>
#include <cstdint>
#include <cstring>
#include <iomanip>
#include <iostream>
#include <xmmintrin.h>
extern "C" double __wrap_asin(double) noexcept;
int main() {
    std::cout << "{\"profile\":\"" << orbiter::production::ReferenceMathProfile()
              << "\",\"rounding\":" << std::fegetround()
              << ",\"mxcsr_control\":" << (_mm_getcsr() & 0xffc0u) << "}\ninput,native\n";
    std::uint64_t input = 0;
    std::size_t count = 0;
    while (std::cin >> std::hex >> input) {
        double value;
        std::memcpy(&value, &input, sizeof(value));
        const double result = __wrap_asin(value);
        std::uint64_t bits;
        std::memcpy(&bits, &result, sizeof(bits));
        std::cout << std::hex << std::setfill('0') << std::setw(16) << input << ','
                  << std::setw(16) << bits << '\n';
        ++count;
    }
    return std::cin.eof() && count && std::cout ? 0 : 1;
}
