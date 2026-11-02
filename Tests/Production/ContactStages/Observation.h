// Licensed under the MIT License
// Diagnostic build only. Reads intermediate values; never supplies physics data.
#pragma once
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <initializer_list>
#include <locale>
#include <stdexcept>
#include <utility>
namespace contact_stages {
struct Call {std::uint64_t index; double seconds, fraction, dt; bool selected;};
inline Call Begin(double seconds,double fraction,double dt) {
    static std::uint64_t index=0;
    // First contact calculations and controlled return touchdown. Fixed-step
    // execution is required; this output never changes either input schedule.
    return {index++,seconds,fraction,dt,seconds<=0.05 || (seconds>=39.0 && seconds<=41.0)};
}
inline void Row(const Call& call,const char* stage,int point,
                std::initializer_list<std::pair<const char*,double>> values) {
    if(!call.selected)return;
    static std::ofstream trace=[] {
        std::ofstream out("contact-stages.jsonl",std::ios::binary);
        out.imbue(std::locale::classic());out<<std::setprecision(17);
        if(!out)throw std::runtime_error("Cannot open diagnostic contact trace");
        return out;
    }();
    trace<<"{\"call\":"<<call.index<<",\"seconds\":"<<call.seconds
         <<",\"fraction\":"<<call.fraction<<",\"dt\":"<<call.dt
         <<",\"stage\":\""<<stage<<"\",\"point\":"<<point<<",\"values\":{";
    bool first=true;
    for(const auto& value:values) {
        if(!std::isfinite(value.second))throw std::runtime_error("Nonfinite diagnostic contact value");
        if(!first)trace<<',';
        trace<<'\"'<<value.first<<"\":"<<value.second;first=false;
    }
    trace<<"}}\n";
    if(!trace)throw std::runtime_error("Cannot write diagnostic contact trace");
}
}
