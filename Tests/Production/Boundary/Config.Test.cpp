// Licensed under the MIT License
#include "Config.h"
#include "OrbiterCelestialData.h"
#include <filesystem>
#include <fstream>
#include <sstream>
#include <stdexcept>
#include <iostream>

namespace {
void require(bool condition, const char* message)
{
    if (!condition) throw std::runtime_error(message);
}
void check(const Config& config)
{
    const auto& physics = config.CfgPhysicsPrm;
    require(physics.nLPropLevel == 1 && physics.PropMode[0] == PROP_RK4,
        "production propagator selection differs");
    require(physics.PropTTgt[0] == 1 && physics.PropATgt[0] == 0.2*RAD,
        "production propagation targets differ");
    require(physics.PropTLim[0] == 1e10 && physics.PropALim[0] == 1e10,
        "production final propagation stage differs");
    require(!physics.bDistributedMass && !physics.bNonsphericalGrav &&
        !physics.bOrbitStabilise && !physics.bAtmWind, "physics flags differ");
    require(config.CfgLogicPrm.bLimitedFuel && config.CfgDebugPrm.FixedStep == 1,
        "fuel/timing configuration differs");
    require(config.CfgVisualPrm.PlanetMaxLevel == 14 && config.CfgVisualPrm.bClouds,
        "planet appearance configuration differs");
    require(std::string(config.CfgVisualPrm.StarImagePath) == "csphere\\milkyway_2020",
        "stock texture path differs");
    require(config.CfgWindowPos.DlgMap.left == -3 && config.CfgWindowPos.DlgMap.bottom == 400,
        "persisted window coordinates differ");
    require(config.GetActiveModules() == std::list<std::string>{"ProductionObserver"},
        "stock CRLF module name was not parsed correctly");
    require(*static_cast<const orbiter::production::UInt32*>(config.GetParam(CFGPRM_SURFACEMAXLEVEL)) == 14,
        "graphics configuration access differs");
}
}
int main(int argc, char** argv)
{
    try {
        if (argc != 2) throw std::runtime_error("test needs an output directory");
        const auto directory = std::filesystem::absolute(argv[1])/"production-config-test";
        std::filesystem::create_directories(directory);
        const auto input = directory/"input.cfg";
        {
            std::ofstream file(input, std::ios::binary);
            file.exceptions(std::ios::badbit|std::ios::failbit);
            file << "DistributedVesselMass = FALSE\r\nNonsphericalGravitySources = FALSE\r\n"
                "StabiliseOrbits = FALSE\r\nAtmosphericWind = FALSE\r\n"
                "PropStages = 1\r\nPropStage0 = " << PROP_RK4 << " 1\r\n"
                "UnlimitedFuel = FALSE\r\nFixedStep = 1\r\nPlanetMaxPatchLevel = 14\r\n"
                "EnableClouds = TRUE\r\nCSphereStarPath = csphere\\milkyway_2020\r\n"
                "WindowWidth = 1280\r\nWindowHeight = 720\r\nDlgMapPos = -3 4 600 400\r\n"
                "ACTIVE_MODULES\r\n  ProductionObserver\r\nEND_MODULES\r\n";
        }
        Config config;
        require(config.CfgPhysicsPrm.nLPropLevel == 4 &&
            config.CfgPhysicsPrm.PropMode[0] == PROP_RK2 &&
            config.CfgPhysicsPrm.PropMode[3] == PROP_RK8,
            "original production defaults differ");
        require(config.Load(input.string().c_str()) && config.FoundFile(), "configuration load failed");
        check(config);
        // The production graphics client owns persistence of its video settings.
        require(config.CfgDevPrm.WinW == 1280 && config.CfgDevPrm.WinH == 720,
            "explicit viewport configuration differs");
        const auto saved = directory/"roundtrip.cfg";
        require(config.Write(saved.string().c_str()) != 0, "configuration save failed");
        Config reloaded;
        require(reloaded.Load(saved.string().c_str()), "configuration reload failed");
        check(reloaded);
        std::istringstream lines(std::string(1024,'x')+"\r\nSun\r\n");
        require(std::string(readline(lines)) == std::string(1024,'x') &&
            std::string(readline(lines)) == "Sun" && !readline(lines),
            "stock growing-line parser differs on CRLF");
        std::cout << "Original production Config loads and round-trips physics, visual and module settings\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
