// Licensed under the MIT License
// Observation only. Enabled explicitly by an engineering fixture, never by UI.
#pragma once
#include "glad.h"
#include "RendererSdk.h"
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <locale>
#include <map>
#include <stdexcept>
#include <vector>
namespace InstrumentEvidence {
inline bool enabled=false;
inline unsigned frame=0;
inline std::filesystem::path directory;
inline std::ofstream text;
inline std::map<SURFHANDLE,unsigned> surfaces;
inline void Begin(const std::filesystem::path& path=".") {
    enabled=std::filesystem::is_regular_file(path/"instrument-evidence.enabled");
    frame=0;surfaces.clear();directory=path;
    if(!enabled)return;
    text.open(directory/"instrument-text.csv",std::ios::binary);
    text.imbue(std::locale::classic());text.exceptions(std::ios::badbit|std::ios::failbit);
    text<<std::setprecision(17)<<"frame,seconds,surface,width,height,x,y,font_height,color,text_hex\n";
}
inline void Text(SURFHANDLE surface,int width,int height,int x,int y,int fontHeight,
                 oapi::UInt32 color,const char* value,int length) {
    if(!enabled)return;
    const auto id=surfaces.emplace(surface,unsigned(surfaces.size())).first->second;
    text<<frame<<','<<oapiGetSimTime()<<','<<id<<','<<width<<','<<height<<','<<x<<','<<y<<','<<fontHeight<<','<<color<<',';
    constexpr char hex[]="0123456789abcdef";
    for(int i=0;i<length;++i){const auto c=static_cast<unsigned char>(value[i]);text<<hex[c>>4]<<hex[c&15];}
    text<<'\n';
}
inline void Rendered() {if(enabled)++frame;}
inline void Frame() {
    if(!enabled || (frame!=20 && frame!=50))return;
    GLint viewport[4]{};glGetIntegerv(GL_VIEWPORT,viewport);
    if(viewport[2]!=1280 || viewport[3]!=720)throw std::runtime_error("Instrument evidence requires 1280x720");
    std::vector<unsigned char> pixels(size_t(viewport[2])*viewport[3]*4);
    glBindFramebuffer(GL_FRAMEBUFFER,0);glReadBuffer(GL_BACK);glPixelStorei(GL_PACK_ALIGNMENT,1);
    glReadPixels(0,0,viewport[2],viewport[3],GL_RGBA,GL_UNSIGNED_BYTE,pixels.data());
    if(glGetError()!=GL_NO_ERROR)throw std::runtime_error("Instrument frame readback failed");
    std::ofstream image(directory/("instrument-"+std::to_string(frame)+".rgba"),std::ios::binary);
    image.exceptions(std::ios::badbit|std::ios::failbit);image.write(reinterpret_cast<const char*>(pixels.data()),pixels.size());
    text.flush();
}
inline void End(){if(text.is_open())text.close();enabled=false;surfaces.clear();}
}
