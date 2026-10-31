// Licensed under the MIT License.
#include "PhysicsTrace.h"
#include <filesystem>
#include <iostream>
#include <limits>
#include <sstream>

namespace {
void require(bool condition, const char *message) {
    if (!condition) throw std::runtime_error(message);
}
template<class F> void fails(F action) {
    bool failed = false;
    try { action(); } catch (const std::runtime_error &) { failed = true; }
    require(failed, "expected trace failure was not reported");
}
struct Comma : std::numpunct<char> {
    char do_decimal_point() const override { return ','; }
};
}

int main(int argc, char **argv) {
    try {
        require(argc == 2, "expected writable test directory");
        const auto dir = std::filesystem::path(argv[1]);
        const auto file = dir / "physics-trace-test.csv";
        const double precise = 1.2345678901234567;
        const orbiter::PhysicsTraceSample sample{0, 0, 51544.5,
            {precise, 0, 0}, {0, 0, 1}, {0, 0, 0, 1}, {0, 0, 0}};
        orbiter::PhysicsTrace trace;
        fails([&] { trace.Write(sample); });
        fails([&] { trace.Open((dir / "missing-parent" / "trace.csv").string()); });
        const auto oldLocale = std::locale();
        std::locale::global(std::locale(oldLocale, new Comma));
        trace.Open(file.string());
        std::locale::global(oldLocale);
        fails([&] { trace.Open(file.string()); });
        trace.Write(sample);
        // Flush must make the row visible before Close (fast process shutdown).
        std::ifstream input(file, std::ios::binary);
        const std::string text((std::istreambuf_iterator<char>(input)), {});
        require(text.find("1.2345678901234567") != std::string::npos,
            "precision or classic locale lost");
        require(text.find('\r') == std::string::npos, "trace must have platform-independent LF");
        input.close();
        for (int field = 0; field < 6; ++field) {
            auto bad = sample;
            const double invalid = std::numeric_limits<double>::quiet_NaN();
            if (field == 0) bad.seconds = invalid;
            if (field == 1) bad.mjd = invalid;
            if (field == 2) bad.position[0] = invalid;
            if (field == 3) bad.velocity[0] = invalid;
            if (field == 4) bad.orientation[0] = invalid;
            if (field == 5) bad.angularVelocity[0] = invalid;
            fails([&] { trace.Write(bad); });
        }
        trace.Close();
        trace.Close();
        fails([&] { trace.Write(sample); });
        // Opening a directory must not be mistaken for a successful output.
        fails([&] { trace.Open(dir.string()); });
#ifndef _WIN32
        if (std::filesystem::exists("/dev/full"))
            fails([&] { trace.Open("/dev/full"); trace.Write(sample); });
#endif
        std::filesystem::remove(file);
        std::cout << "PASS: trace precision, locale, flush, nonfinite and I/O failures\n";
        return 0;
    } catch (const std::exception &error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
