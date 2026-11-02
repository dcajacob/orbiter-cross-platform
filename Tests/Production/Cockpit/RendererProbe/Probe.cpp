// Licensed under the MIT License
// Renderer-only integration: no replacement world, vessel or instruments.
#include "Production/NativeGraphics.h"
#include "Production/NativeModule.h"
#include "Config.h"
#include "TimeData.h"
#define GL_GLEXT_PROTOTYPES
#include <GL/gl.h>
#include "OVP/OGLClient/Texture.h"
#include <fstream>
#include <iostream>
#include <stdexcept>
using namespace orbiter::production;
namespace {void require(bool ok,const char* message){if(!ok)throw std::runtime_error(message);}}
int main(int argc,char** argv){try{
    require(argc==5,"Usage: renderer-probe <module> <assets> <planets> <report.json>");
    Config settings;TimeData time;time.Reset(51982.5);
    const auto assets=std::filesystem::absolute(argv[2]);
    ResourceResolver program(assets),textures(assets/"Textures"),high(assets/"Textures2"),planets(std::filesystem::absolute(argv[3])/"Textures");
    NativeRenderContext context;context.configuration=&settings;context.time=&time;context.programFiles=&program;
    context.textures=&textures;context.highTextures=&high;context.planetTextures=&planets;BindNativeRenderContext(&context);
    NativeModule module(std::filesystem::absolute(argv[1]),ORBITER_NATIVE_GRAPHICS,&context);
    auto* client=static_cast<NativeGraphics*>(module.Instance());context.graphics=client;client->Open();
    auto surface=client->CreateSurfaceResource(128,64);require(surface,"Real render target unavailable");
    auto font=client->CreateFontResource(-14,false,"Fixed",FONT_NORMAL,0);auto* pad=client->AcquireSketchpad(surface);
    require(pad && font,"Original Sketchpad/font unavailable");pad->SetFont(font);
    const auto metrics=pad->GetCharSize(),height=metrics&0xffff,width=metrics>>16;
    const bool valid=height>0 && height<64 && width>0 && width<64;
    if(valid){pad->SetTextColor(0x0000ff00);require(pad->Text(4,4,"Orbit 123.45",11),"Actual text draw failed");}
    client->ReleaseSketchpadResource(pad);client->ReleaseFontResource(font);
    auto* texture=static_cast<OGLTexture*>(surface);glBindFramebuffer(GL_FRAMEBUFFER,texture->m_FBO);
    unsigned char pixels[128*64*4];glReadPixels(0,0,128,64,GL_RGBA,GL_UNSIGNED_BYTE,pixels);glBindFramebuffer(GL_FRAMEBUFFER,0);
    const auto error=glGetError();unsigned green=0;
    for(unsigned i=0;i<sizeof(pixels);i+=4)if(pixels[i+1]>pixels[i]+20 && pixels[i+1]>pixels[i+2]+20)++green;
    client->ReleaseTextureResource(surface);const bool rejected=client->CreateSurfaceResource(0,64)==nullptr;
    client->CloseSession();client->Close();context.graphics=nullptr;
    require(valid,"Negative font height produced invalid instrument metrics");require(error==GL_NO_ERROR,"Actual instrument render produced a GL error");
    require(green>10,"Actual font produced no colored glyph pixels");require(rejected,"Invalid surface dimensions were accepted");
    std::ofstream report(argv[4]);report.exceptions(std::ios::badbit|std::ios::failbit);
    report<<"{\"status\":\"passed\",\"requested_height\":-14,\"character_width\":"<<width<<",\"character_height\":"<<height
          <<",\"glyph_pixels\":"<<green<<",\"invalid_surface_rejected\":true,\"gl_error\":0}\n";
    std::cout<<"Actual font metrics "<<width<<'x'<<height<<"; green glyph pixels "<<green<<'\n';BindNativeRenderContext(nullptr);
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';BindNativeRenderContext(nullptr);return 1;}}
