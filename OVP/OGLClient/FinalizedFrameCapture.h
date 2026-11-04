// Licensed under the MIT License
// Private evidence policy. No public SDK layout or simulator clock is changed.
#pragma once
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <limits>
#include <ostream>
#include <stdexcept>
#include <string>

namespace Evidence {
class FinalizedFrameCapture {
    unsigned requested=0,selected=0;
public:
    using Reader=unsigned(*)(unsigned);
    static constexpr const char* Marker(){return "remaining-stock-finalized-frame-v2.txt";}
    static constexpr const char* Protocol(){return "remaining-stock-matched-clock-v2";}
    static constexpr const char* Observer(){return "OrbiterRemainingStockFinalizedTickV2";}
    void Begin(const std::filesystem::path& root) {
        requested=selected=0;
        const auto path=root/Marker();
        if(!std::filesystem::exists(path))return;
        std::ifstream source(path);std::string protocol,extra;std::uint64_t tick=0;
        if(!(source>>protocol>>tick) || protocol!=Protocol() || !tick || tick>10000000 || source>>extra)
            throw std::runtime_error("Invalid finalized-frame evidence descriptor");
        requested=static_cast<unsigned>(tick);
    }
    bool Enabled()const {return requested!=0;}
    bool Select(Reader reader) {
        if(!Enabled())throw std::logic_error("Finalized-frame selection is not configured");
        if(!reader)throw std::runtime_error("Finalized-frame evidence observer missing");
        const auto tick=reader(2);
        if(tick==(std::numeric_limits<unsigned>::max)())throw std::runtime_error("Finalized-frame evidence observer ABI differs");
        if(tick>requested)throw std::runtime_error("Missed requested finalized-frame graphics evidence");
        if(tick!=requested)return false;
        selected=tick;return true;
    }
    void Summary(std::ostream& stream)const {
        if(Enabled())stream<<",\"capture_protocol\":\""<<Protocol()<<"\",\"finalized_tick\":"<<selected;
    }
};
}
