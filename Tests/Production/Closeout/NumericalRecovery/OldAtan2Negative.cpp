// Observe the unchanged pre-fix binding with the exact captured binary64 inputs.
#include "Runtime.h"
#include <charconv>
#include <chrono>
#include <cstdint>
#include <cstring>
#include <iomanip>
#include <iostream>
#include <limits>
#include <string_view>
#include <thread>

extern "C" double __wrap_atan2(double, double) noexcept;

int main(int argc, char** argv) {
    static_assert(sizeof(double) == sizeof(std::uint64_t) && std::numeric_limits<double>::is_iec559);
    if (argc != 3) return 2;
    double arguments[2]{};
    for (int i = 0; i < 2; ++i) {
        const std::string_view text(argv[i+1]);
        std::uint64_t bits{};
        const auto converted = std::from_chars(text.data(), text.data()+text.size(), bits, 16);
        if (text.size()!=16 || converted.ec!=std::errc{} || converted.ptr!=text.data()+text.size()) return 2;
        std::memcpy(&arguments[i], &bits, sizeof(bits));
    }
    const char* profile=orbiter::production::ReferenceMathProfile();
    const double result=__wrap_atan2(arguments[0], arguments[1]);
    std::uint64_t bits{};
    std::memcpy(&bits, &result, sizeof(bits));
    // Give the parent time to record the actual OS process identity.
    std::this_thread::sleep_for(std::chrono::milliseconds(50));
    std::cout<<profile<<'\n'<<std::hex<<std::setw(16)<<std::setfill('0')<<bits<<'\n';
}
