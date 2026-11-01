// Licensed under the MIT License
#pragma once
#include <array>
#include <cstdint>
#include <vector>
namespace orbiter::production {
struct FlightKeyEvent {std::uint32_t code=0;bool down=false;};
struct FlightInput {
    std::array<char,256> keys{};
    std::vector<FlightKeyEvent> events;
    std::int32_t x=0,y=0,rz=0;
    bool alternate=false;
    double throttle=-1; // -1: no armed device throttle; otherwise [0,1].
};
}
