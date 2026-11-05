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

// Buffered edges may span a complete chord before the next render poll. Recover
// their starting state, then advance in order without changing immediate input.
class BufferedKeyState {
    std::array<char,256> keys;
public:
    explicit BufferedKeyState(const FlightInput& input):keys(input.keys) {
        for(auto event=input.events.rbegin();event!=input.events.rend();++event)
            if(event->code<keys.size())keys[event->code]=event->down?0:char(0x80);
    }
    std::array<char,256>& Advance(const FlightKeyEvent& event) {
        if(event.code<keys.size())keys[event.code]=event.down?char(0x80):0;
        return keys;
    }
};
}
