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
struct Call {std::uint64_t index; double seconds, fraction, dt; const char* object; bool selected;};
inline Call& Current() {static Call call{};return call;}
inline Call Begin(double seconds,double fraction,double dt,const char* object) {
    static std::uint64_t index=0;
    // Includes the first force divergence and the controlled return touchdown.
    // Fixed-step execution is required; inputs are never changed by this output.
    Current()={index++,seconds,fraction,dt,object,seconds<=41.0};
    return Current();
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
         <<",\"object\":\""<<call.object<<"\",\"stage\":\""<<stage<<"\",\"point\":"<<point<<",\"values\":{";
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
