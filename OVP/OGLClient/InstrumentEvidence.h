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
#include <algorithm>
#include <stdexcept>
#include <string>
#include <vector>
namespace InstrumentEvidence {
inline bool enabled=false;
inline unsigned frame=0;
inline unsigned overlay=0;
inline std::filesystem::path directory;
inline std::ofstream text,geometry,blits;
inline std::map<SURFHANDLE,unsigned> surfaces;
inline void Begin(const std::filesystem::path& path=".") {
    enabled=std::filesystem::is_regular_file(path/"instrument-evidence.enabled");
    frame=overlay=0;surfaces.clear();directory=path;
    if(!enabled)return;
    text.open(directory/"instrument-text.csv",std::ios::binary);
    text.imbue(std::locale::classic());text.exceptions(std::ios::badbit|std::ios::failbit);
    text<<std::setprecision(17)<<"frame,seconds,surface,width,height,x,y,font_height,color,text_hex\n";
    geometry.open(directory/"instrument-geometry.csv",std::ios::binary);
    blits.open(directory/"instrument-self-blits.csv",std::ios::binary);
    for(auto* file:{&geometry,&blits}){file->imbue(std::locale::classic());file->exceptions(std::ios::badbit|std::ios::failbit);*file<<std::setprecision(17);}
    geometry<<"frame,seconds,overlay,group,vertex,texture,x,y,u,v\n";
    blits<<"frame,seconds,x,y,source_x,source_y,width,height,flags\n";
}
inline bool SampleGeometry(){if(!enabled)return false;const double time=oapiGetSimTime();return time==5. || time==12.5;}
inline void Overlay(MESHHANDLE mesh,const MATRIX3* transform){
    if(!enabled)return;++overlay;if(!SampleGeometry())return;
    for(oapi::UInt32 i=0;i<oapiMeshGroupCount(mesh);++i){
        auto* group=oapiMeshGroup(mesh,i);if(group->UsrFlag&2)continue;
        for(oapi::UInt32 j=0;j<group->nVtx;++j){const auto& v=group->Vtx[j];
            geometry<<frame<<','<<oapiGetSimTime()<<','<<overlay<<','<<i<<','<<j<<','<<group->TexIdx<<','
                <<float(transform->m11)*v.x+float(transform->m13)<<','<<float(transform->m22)*v.y+float(transform->m23)<<','<<v.tu<<','<<v.tv<<'\n';
        }
    }
}
inline void SelfBlt(SURFHANDLE target,int x,int y,SURFHANDLE source,int sx,int sy,int w,int h,int flags){
    if(enabled && target==source)blits<<frame<<','<<oapiGetSimTime()<<','<<x<<','<<y<<','<<sx<<','<<sy<<','<<w<<','<<h<<','<<flags<<'\n';
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
inline bool CaptureFrame(){return enabled && (frame==20 || frame==50);}
inline void Mfd(unsigned index,GLuint texture,int width,int height){
    if(!CaptureFrame())return;
    std::vector<unsigned char> pixels(size_t(width)*height*4);GLint previous=0;glGetIntegerv(GL_TEXTURE_BINDING_2D,&previous);
    glBindTexture(GL_TEXTURE_2D,texture);glGetTexImage(GL_TEXTURE_2D,0,GL_RGBA,GL_UNSIGNED_BYTE,pixels.data());glBindTexture(GL_TEXTURE_2D,previous);
    if(glGetError()!=GL_NO_ERROR)throw std::runtime_error("Actual MFD texture readback failed");
    unsigned colored=0,nonwhite=0;
    for(size_t i=0;i<pixels.size();i+=4){const int r=pixels[i],g=pixels[i+1],b=pixels[i+2];if(r<240 || g<240 || b<240)++nonwhite;if(std::max(r,std::max(g,b))-std::min(r,std::min(g,b))>25)++colored;}
    const auto base="mfd-"+std::to_string(index)+"-"+std::to_string(frame);
    std::ofstream image(directory/(base+".rgba"),std::ios::binary);image.exceptions(std::ios::badbit|std::ios::failbit);image.write(reinterpret_cast<const char*>(pixels.data()),pixels.size());
    std::ofstream report(directory/(base+".json"));report.exceptions(std::ios::badbit|std::ios::failbit);
    report<<"{\"width\":"<<width<<",\"height\":"<<height<<",\"colored_pixels\":"<<colored<<",\"nonwhite_pixels\":"<<nonwhite<<"}\n";
}
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
inline void End(){for(auto* file:{&text,&geometry,&blits})if(file->is_open())file->close();enabled=false;surfaces.clear();}
}
