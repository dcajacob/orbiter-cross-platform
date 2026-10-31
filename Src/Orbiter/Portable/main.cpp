// Licensed under the MIT License.
#include "SimulationSession.h"
#include <cmath>
#include <iostream>
#include <limits>
#include <locale>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>

namespace {
double StepLength(const std::string &text) {
    std::istringstream stream(text);
    stream.imbue(std::locale::classic());
    double value;
    if (!(stream >> value) || !std::isfinite(value) || value <= 0 || !std::isfinite(1/value))
        throw std::runtime_error("--fixed-step requires a finite positive number");
    stream >> std::ws;
    if (!stream.eof()) throw std::runtime_error("invalid --fixed-step suffix");
    return value;
}
std::size_t StepCount(const std::string &text) {
    if (text.empty() || text.find_first_not_of("0123456789") != std::string::npos)
        throw std::runtime_error("--steps requires a positive integer");
    const auto value = std::stoull(text);
    if (!value || value > std::numeric_limits<std::size_t>::max())
        throw std::runtime_error("--steps is outside the supported range");
    return static_cast<std::size_t>(value);
}
}

int main(int argc, char **argv) {
    try {
        std::map<std::string,std::string> options;
        bool help = false;
        for (int i = 1; i < argc; ++i) {
            std::string key(argv[i]), value;
            if (key == "--help") { help = true; continue; }
            const auto equals = key.find('=');
            if (equals != std::string::npos) {
                value = key.substr(equals+1);
                key.resize(equals);
            } else {
                if (i+1 == argc) throw std::runtime_error("missing option value: " + key);
                value = argv[++i];
            }
            if (key != "--scenario" && key != "--trace" && key != "--fixed-step" && key != "--steps")
                throw std::runtime_error("unknown option: " + key);
            if (value.empty() || !options.emplace(key,value).second)
                throw std::runtime_error("empty or duplicate option: " + key);
        }
        if (help) {
            std::cout << "orbiter-headless --scenario <path> --fixed-step 1 --steps 6000 --trace <path>\n"
                         "One fixed spherical primary and one unpowered generic vessel.\n"
                         "Defaults: --fixed-step 1 --steps 6000. Configurations are read from the scenario bundle.\n";
            return 0;
        }
        if (!options.count("--scenario") || !options.count("--trace"))
            throw std::runtime_error("--scenario and --trace are required (see --help)");
        const double step = options.count("--fixed-step") ? StepLength(options.at("--fixed-step")) : 1;
        const auto steps = options.count("--steps") ? StepCount(options.at("--steps")) : 6000;
        auto session = orbiter::portable::SimulationSession::Load(options.at("--scenario"),step);
        if (session.IsInputFile(options.at("--trace")))
            throw std::runtime_error("trace output would overwrite a scenario/configuration input");
        orbiter::PhysicsTrace trace;
        trace.Open(options.at("--trace"));
        trace.Write(session.ReadState());
        for (std::size_t i = 0; i < steps; ++i) {
            session.Step();
            if ((i+1)%10 == 0 || i+1 == steps) trace.Write(session.ReadState());
        }
        trace.Close();
        std::cout << "Completed " << steps << " fixed steps; state trace saved.\n";
        return 0;
    } catch (const std::exception &error) {
        std::cerr << "orbiter-headless: " << error.what() << '\n';
        return 1;
    }
}
