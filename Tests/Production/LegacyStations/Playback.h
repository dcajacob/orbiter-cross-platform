// Licensed under the MIT License
// Read-only per-vessel playback status, including non-focus vessels.
#pragma once
#include "../StockVessels/Observation.h"
namespace legacy_playback {
inline void open(std::ofstream& stream) {
    stock_vessels::open(stream,"stock-playback.csv","tick,object,playback");
}
inline void snapshot(std::ofstream& stream,unsigned tick) {
    for(unsigned index=0;index<oapiGetVesselCount();++index) {
        auto* vessel=oapiGetVesselInterface(oapiGetVesselByIndex(index));
        stock_vessels::require(vessel!=nullptr,"Playback vessel missing");
        stream<<tick<<','<<stock_vessels::csv(vessel->GetName())<<','<<vessel->Playback()<<'\n';
    }
    stream.flush();
}
}
