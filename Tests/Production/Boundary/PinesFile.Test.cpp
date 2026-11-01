// Licensed under the MIT License
#include "PinesGrav.h"
#include <algorithm>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>

namespace fs = std::filesystem;
void require(bool value, const char* message) { if (!value) throw std::runtime_error(message); }
const char* model =
    "6378.1363,398600.4415,0,2,2,1,0,0\n"
    "1,0,0,0,0,0\n1,1,0,0,0,0\n2,0,-0.00044721359549995793,0,0,0\n"
    "2,1,0,0,0,0\n2,2,0,0,0,0"; // A final newline is optional.
void write(const fs::path& path, const std::string& text)
{
    std::ofstream output(path, std::ios::binary);
    output.exceptions(std::ios::badbit | std::ios::failbit);
    output << text;
}
int main(int argc, char** argv)
{
    try {
        require(argc == 3, "Expected scratch and stock model directories");
        const auto path = fs::path(argv[1])/"pines-transaction-test.tab";
        write(path, model);
        PinesGravProp gravity(nullptr);
        int loaded = -7, maximum = -9;
        require(gravity.ReadGravityModel(path, 32, loaded, maximum) == 0 &&
            loaded == 5 && maximum == 5 && gravity.GetCoeffCutoff() == 2, "File limit was not applied");
        const Vector position(3000, 4000, 5000);
        const Vector expected = gravity.GetPinesGrav(position, 2, 2);
        const auto unchanged = [&] {
            const Vector actual = gravity.GetPinesGrav(position, 2, 2);
            require(actual.x == expected.x && actual.y == expected.y && actual.z == expected.z &&
                    gravity.GetCoeffCutoff() == 2, "Failed reload modified the active model");
        };
        require(fs::remove(path), "Gravity model remained open after loading");
        loaded = -7; maximum = -9;
        require(gravity.ReadGravityModel(path, 32, loaded, maximum) == 1, "Missing model was accepted");
        unchanged();
        const auto rejected = [&](const std::string& text, int result) {
            write(path, text);
            require(gravity.ReadGravityModel(path, 32, loaded, maximum) == result, "Invalid model was accepted");
            require(loaded == -7 && maximum == -9, "Failed load published its metadata");
            unchanged();
            require(fs::remove(path), "Failed parsing leaked an open file");
        };
        rejected("invalid header\n", 3);
        rejected("6378,nan,0,2,2,1,0,0\n", 3);
        rejected("6378,398600,0,4294967295,4294967295,1,0,0\n", 3);
        rejected("6378,398600,0,4294967298,4294967298,1,0,0\n", 3);
        rejected("6378,398600,0,2,2,0,0,0\n", 3);
        rejected(std::string(600, '1')+"\n", 3);
        rejected("6378,398600,0,2,2,1,0,0\n1,0,0,0\n", 4);
        rejected("6378,398600,0,2,2,1,0,0\n1,1,0,0\n", 4);
        rejected("6378,398600,0,2,2,1,0,0\n4294967297,0,0,0\n", 4);
        rejected("6378,398600,0,2,2,1,0,0\n1,0,nan,0\n", 4);
        write(path, model);
        require(gravity.ReadGravityModel(path, -1, loaded, maximum) == 3, "Negative cutoff was accepted");
        unchanged();
        write(path, "6378,398600,0,65532,65532,1,0,0\n");
        require(gravity.ReadGravityModel(path, std::numeric_limits<int>::max(), loaded, maximum) == 4,
                "Truncated model trusted huge declared dimensions before allocation");
        unchanged();
        std::string crlf;
        for (char ch : std::string(model)) crlf += ch == '\n' ? "\r\n" : std::string(1, ch);
        write(path, crlf);
        require(gravity.ReadGravityModel(path, 2, loaded, maximum) == 0, "CRLF model was rejected");
        unchanged();
        write(path, model);
        for (int i = 0; i < 20; ++i) {
            require(gravity.ReadGravityModel(path, std::numeric_limits<int>::max(), loaded, maximum) == 0 &&
                    loaded == 5 && maximum == 5, "Requested cutoff overflowed before model clamping");
            unchanged();
        }
        require(fs::remove(path), "Repeated reloads retained a file handle");
        for (const char* name : {"egm96_to360.tab", "jgl165p1.sha", "jgmro_120f_sha.tab",
                "jgmess_160a_sha.tab", "mod_shgj120p.a01", "JGDWN_VES20H_SHA.TAB", "JGDWN_C70E01_SHA.TAB"}) {
            require(gravity.ReadGravityModel(fs::path(argv[2])/name, 32, loaded, maximum) == 0,
                    "Tracked stock coefficient model was rejected");
            const int degree = std::min(4u, gravity.GetCoeffCutoff());
            const Vector acceleration = gravity.GetPinesGrav(Vector(10000, 2000, 3000), degree, degree);
            require(std::isfinite(acceleration.x) && std::isfinite(acceleration.y) && std::isfinite(acceleration.z),
                    "Tracked stock model produced a nonfinite force");
        }
        std::cout << "Production Pines: transactional parsing, model limits, reloads and explicit failures passed\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n'; return 1;
    }
}
