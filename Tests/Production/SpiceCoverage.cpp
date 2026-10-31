// Copyright (c) Orbiter contributors. Licensed under the MIT License.
// Audit the actual pinned CSPICE kernels; this is not a production world/session.
#include "SpiceUsr.h"
#include <cmath>
#include <filesystem>
#include <iomanip>
#include <iostream>
#include <locale>
#include <sstream>
#include <stdexcept>
#include <string>

void check(const std::string &context) {
    if (failed_c()) {
        char message[4096]{};
        getmsg_c("LONG", sizeof(message), message);
        reset_c();
        throw std::runtime_error(context + ": " + message);
    }
}
int main(int argc, char **argv) {
    try {
        if (argc != 2) throw std::runtime_error("usage: orbiter-spice-data-audit <data-root>; TSV queries on stdin");
        erract_c("SET", 0, const_cast<char *>("RETURN"));
        errprt_c("SET", 0, const_cast<char *>("NONE"));
        for (const char *name : {"naif0012.tls", "pck00011.tpc", "orbiter.bsp"}) {
            std::string path = (std::filesystem::path(argv[1])/"Kernels"/name).string();
            furnsh_c(path.c_str());
            check("load " + path);
        }
        std::cout.imbue(std::locale::classic());
        std::cin.imbue(std::locale::classic());
        std::cout << std::setprecision(17) << "body,origin,mjd,x,y,z,vx,vy,vz\n";
        std::string line;
        size_t count = 0;
        while (std::getline(std::cin, line)) {
            std::istringstream input(line);
            input.imbue(std::locale::classic());
            std::string body, origin;
            double mjd = 0;
            if (!std::getline(input, body, '\t') || !std::getline(input, origin, '\t') || !(input >> mjd) || !std::isfinite(mjd))
                throw std::runtime_error("invalid body/origin/MJD query");
            input >> std::ws;
            if (!input.eof()) throw std::runtime_error("unexpected query fields");
            // Same epoch convention as production spice.cpp clbkEphemeris.
            const double et = (mjd-51544.5)*86400;
            double state[6]{}, lightTime = 0;
            spkezr_c(body.c_str(), et, "ECLIPJ2000", "NONE", origin.c_str(), state, &lightTime);
            check("kernel coverage for " + body + " at MJD " + std::to_string(mjd));
            std::cout << std::quoted(body) << ',' << std::quoted(origin) << ',' << mjd;
            for (double value : state) {
                if (!std::isfinite(value)) throw std::runtime_error("nonfinite SPICE state");
                std::cout << ',' << value*1000; // native CSPICE km -> SI metres
            }
            std::cout << '\n';
            ++count;
        }
        if (!std::cin.eof() || count == 0 || !std::cout) throw std::runtime_error("incomplete query IO");
        std::cerr << "CSPICE " << tkvrsn_c("TOOLKIT") << "; " << count << " coverage queries passed\n";
        kclear_c();
        return 0;
    } catch (const std::exception &error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
