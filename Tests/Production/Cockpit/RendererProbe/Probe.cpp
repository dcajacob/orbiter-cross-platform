// Licensed under the MIT License
// Renderer-only integration: no replacement world, vessel or instruments.
#include "Production/NativeGraphics.h"
#include "Production/NativeModule.h"
#include "Config.h"
#include "TimeData.h"
#include "Mesh.h"
#include "Production/MeshServices.h"
#include <cmath>
#include <limits>
#define GL_GLEXT_PROTOTYPES
#include <GL/gl.h>
#include "OVP/OGLClient/Texture.h"
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <vector>
#include <algorithm>
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
    auto* client=static_cast<NativeGraphics*>(module.Instance());context.graphics=client;
    constexpr unsigned cycles=20;
    for(unsigned cycle=0;cycle<cycles;++cycle){
    context.evidence=std::filesystem::absolute(argv[4]).parent_path()/("context-"+std::to_string(cycle));
    client->Open();
    require(client->DesktopHeight()>0,"Real native primary display metrics unavailable");
    oapi::UInt32 capability=99;require(client->clbkGetRenderParam(RP_COLOURDEPTH,&capability) && capability==32,"Native renderer capability query differs");
    capability=99;require(!client->clbkGetRenderParam(0xffffffff,&capability) && capability==99,"Unknown renderer capability returned invented data");
    auto shared=client->clbkCreateTexture(2,2);require(shared,"Native blank instrument texture unavailable");
    oapi::UInt32 sharedWidth=0,sharedHeight=0;
    require(client->clbkGetSurfaceSize(shared,&sharedWidth,&sharedHeight) && sharedWidth==2 && sharedHeight==2,"Native texture-size callback differs");
    const GLuint sharedId=static_cast<OGLTexture*>(shared)->m_TexId;
    client->clbkIncrSurfaceRef(shared);require(client->clbkReleaseSurface(shared),"Native shared surface release failed");
    require(client->clbkFillSurface(shared,0x0000ff) && glIsTexture(sharedId),"Native shared surface was destroyed while still referenced");
    require(client->clbkReleaseSurface(shared) && !glIsTexture(sharedId),"Native last surface release retained a GPU texture");
    require(glGetError()==GL_NO_ERROR,"Context reinitialization produced a GL error");
    glDebugMessageCallback([](GLenum,GLenum type,GLuint,GLenum,GLsizei,const GLchar* message,const void*){
        if(type==GL_DEBUG_TYPE_ERROR)std::cerr<<"Actual GL error: "<<message<<'\n';
    },nullptr);glEnable(GL_DEBUG_OUTPUT);glEnable(GL_DEBUG_OUTPUT_SYNCHRONOUS);
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
    auto source=client->clbkCreateSurfaceEx(16,16,OAPISURFACE_RENDERTARGET|OAPISURFACE_SKETCHPAD);
    auto target=client->clbkCreateSurfaceEx(24,24,OAPISURFACE_RENDERTARGET|OAPISURFACE_TEXTURE);
    require(source && target,"Instrument callback surface allocation failed");
    require(client->clbkFillSurface(source,client->clbkGetDeviceColour(20,70,130)),"Device-color fill failed");
    require(client->clbkFillSurface(target,0),"Target fill failed");
    auto brush=oapiCreateBrush(255);require(brush,"Instrument brush callback failed");
    pad=client->clbkGetSketchpad(source);require(pad,"Callback Sketchpad unavailable");
    pad->SetPen(nullptr);pad->SetBrush(brush);pad->Rectangle(3,3,11,11);
    client->clbkReleaseSketchpad(pad);oapiReleaseBrush(brush);
    require(client->clbkBlt(target,4,4,source),"Complete instrument surface copy failed");
    const auto read=[&](SURFHANDLE handle,int w,int h){
        std::vector<unsigned char> data(size_t(w)*h*4);
        glBindTexture(GL_TEXTURE_2D,static_cast<OGLTexture*>(handle)->m_TexId);
        glGetTexImage(GL_TEXTURE_2D,0,GL_RGBA,GL_UNSIGNED_BYTE,data.data());glBindTexture(GL_TEXTURE_2D,0);return data;
    };
    const auto sourcePixels=read(source,16,16),copied=read(target,24,24);
    unsigned filled=0,painted=0;
    for(int y=0;y<16;++y)for(int x=0;x<16;++x){
        const auto offset=size_t(y*16+x)*4;
        const auto r=sourcePixels[offset],g=sourcePixels[offset+1],b=sourcePixels[offset+2];
        if(r==20 && g==70 && b==130)++filled;
        if(r==255 && g==0 && b==0)++painted;
        require(std::equal(sourcePixels.begin()+offset,sourcePixels.begin()+offset+4,copied.begin()+size_t((y+4)*24+x+4)*4),
            "Complete instrument surface copy changed pixel coordinates or colors");
    }
    require(filled>100 && painted>20,"Instrument brush or device color produced incorrect pixels");
    oapiBlt(target,source,0,0,0,0,16,16);
    const auto apiCopied=read(target,24,24);
    for(int y=0;y<16;++y) require(std::equal(sourcePixels.begin()+size_t(y)*16*4,sourcePixels.begin()+size_t(y+1)*16*4,
        apiCopied.begin()+size_t(y)*24*4),"Native SDK rectangular surface copy differs from its source");
    bool obsoleteRejected=false;try{oapiBlt(target,source,0,0,0,0,16,16,0);}catch(const std::runtime_error&){obsoleteRejected=true;}
    require(obsoleteRejected,"Unsupported obsolete SDK color key silently succeeded");
    require(client->clbkBlt(target,1,1,target,0,0,16,16),"Overlapping instrument copy failed");
    const auto overlap=read(target,24,24);
    for(int y=0;y<16;++y) require(std::equal(apiCopied.begin()+size_t(y)*24*4,apiCopied.begin()+size_t(y)*24*4+16*4,
        overlap.begin()+size_t((y+1)*24+1)*4),"Overlapping instrument copy did not snapshot its source");
    require(glGetError()==GL_NO_ERROR,"Instrument brush/fill/blit callbacks produced a GL error");
    // An isolated graphics primitive tests the real panel callback. It is not
    // a substitute for a stock vessel, panel or production cockpit session.
    MeshServices meshServices;meshServices.context=client;
    meshServices.path=[](void*,const char*)->std::filesystem::path{throw std::logic_error("Panel primitive loads no mesh file");};
    meshServices.loadTexture=[](void*,const char*,oapi::UInt32)->MeshSurface{throw std::logic_error("Panel primitive loads no mesh textures");};
    meshServices.releaseTexture=[](void* context,MeshSurface texture){static_cast<NativeGraphics*>(context)->clbkReleaseSurface(texture);};
    meshServices.error=[](void*,const char* message){throw std::runtime_error(message);};
    meshServices.allocation=[](void*,const char*,int){};
    const auto previousMesh=BindMeshServices(meshServices);
    {
        Mesh panel;NTVERTEX vertices[4]={{16,16,0,0,0,1,0,0},{32,16,0,0,0,1,1,0},{16,32,0,0,0,1,0,1},{32,32,0,0,0,1,1,1}};
        oapi::UInt16 indices[6]={0,1,2,2,1,3};panel.AddGroup(vertices,4,indices,6,SPEC_DEFAULT,0,0,0,true);
        MATRIX3 transform={1,0,0,0,1,0,0,0,1};SURFHANDLE surfaces[]={source};
        for(bool additive:{false,true})for(float opacity:{1.f,.5f,0.f}) {
            glBindFramebuffer(GL_FRAMEBUFFER,0);glViewport(0,0,1280,720);glClearColor(0,0,.25f,1);glClear(GL_COLOR_BUFFER_BIT);
            client->clbkRender2DPanel(surfaces,&panel,&transform,opacity,additive);
            unsigned char pixel[4]{};glReadPixels(24,720-24,1,1,GL_RGBA,GL_UNSIGNED_BYTE,pixel);
            const int expectedBlue=int(std::lround(64*(additive?1:1-opacity)));
            const bool correct=std::abs(int(pixel[0])-int(std::lround(255*opacity)))<=1 && pixel[1]==0 && std::abs(int(pixel[2])-expectedBlue)<=1;
            if(!correct)std::cerr<<"Panel opacity="<<opacity<<" actual RGBA="<<int(pixel[0])<<','<<int(pixel[1])<<','<<int(pixel[2])<<','<<int(pixel[3])<<'\n';
            require(correct,
                "Actual instrument panel callback ignores or misapplies opacity");
        }
        bool invalidOpacity=false;
        try{client->clbkRender2DPanel(surfaces,&panel,&transform,std::numeric_limits<float>::quiet_NaN(),false);}catch(const std::invalid_argument&){invalidOpacity=true;}
        require(invalidOpacity,"Nonfinite panel opacity silently succeeded");
        require(glGetError()==GL_NO_ERROR,"Actual panel opacity callback produced a GL error");
    }
    BindMeshServices(previousMesh);
    require(client->clbkScaleBlt(target,0,0,8,8,source,0,0,16,16),"Native instrument scale-copy callback failed");
    const auto scaled=read(target,24,24);const auto scaledCenter=size_t(4*24+4)*4;
    require(scaled[scaledCenter]==255 && scaled[scaledCenter+1]==0 && scaled[scaledCenter+2]==0,"Panel opacity leaked into the following instrument copy");
    oapiClearSurface(target);const auto cleared=read(target,24,24);
    for(size_t i=0;i<cleared.size();i+=4)require(cleared[i]==0 && cleared[i+1]==0 && cleared[i+2]==0,"SDK surface clear left colored pixels");
    oapiDestroySurface(source);oapiDestroySurface(target);
    auto stock=client->LoadTextureResource("shuttlepb.dds",4);require(stock,"Actual compressed stock texture missing");
    auto* writable=static_cast<OGLTexture*>(stock);GLint compressedBefore=0,compressedAfter=0;
    glBindTexture(GL_TEXTURE_2D,writable->m_TexId);glGetTexLevelParameteriv(GL_TEXTURE_2D,0,GL_TEXTURE_COMPRESSED,&compressedBefore);
    std::vector<unsigned char> before(size_t(writable->m_Width)*writable->m_Height*4),after(before.size());
    glGetTexImage(GL_TEXTURE_2D,0,GL_RGBA,GL_UNSIGNED_BYTE,before.data());glBindTexture(GL_TEXTURE_2D,0);
    font=client->CreateFontResource(-14,false,"Fixed",FONT_NORMAL,0);pad=client->AcquireSketchpad(stock);
    pad->SetFont(font);pad->SetTextColor(0x0000ff00);require(pad->Text(4,4,"Orbit 123.45",11),"Stock texture drawing failed");
    client->ReleaseSketchpadResource(pad);client->ReleaseFontResource(font);
    glBindTexture(GL_TEXTURE_2D,writable->m_TexId);glGetTexLevelParameteriv(GL_TEXTURE_2D,0,GL_TEXTURE_COMPRESSED,&compressedAfter);
    glGetTexImage(GL_TEXTURE_2D,0,GL_RGBA,GL_UNSIGNED_BYTE,after.data());glBindTexture(GL_TEXTURE_2D,0);
    unsigned changed=0;for(size_t i=0;i<before.size();i+=4)if(!std::equal(before.begin()+i,before.begin()+i+4,after.begin()+i))++changed;
    const auto stockError=glGetError();client->ReleaseTextureResource(stock);
    client->CloseSession();client->Close();
    require(valid,"Negative font height produced invalid instrument metrics");require(error==GL_NO_ERROR,"Actual instrument render produced a GL error");
    require(green>10,"Actual font produced no colored glyph pixels");require(rejected,"Invalid surface dimensions were accepted");
    require(compressedBefore && !compressedAfter && changed>10 && changed<before.size()/40,"Compressed stock drawing target lost its contents or failed to update");
    require(stockError==GL_NO_ERROR,"Compressed stock drawing target produced a GL error");
    if(cycle+1!=cycles)continue;
    std::ofstream report(argv[4]);report.exceptions(std::ios::badbit|std::ios::failbit);
    report<<"{\"status\":\"passed\",\"requested_height\":-14,\"character_width\":"<<width<<",\"character_height\":"<<height
          <<",\"surface_callback_pixels_verified\":true,\"panel_opacity_and_additive_pixels_verified\":true,\"surface_references_verified\":true,\"context_cycles\":"<<cycles<<",\"glyph_pixels\":"<<green<<",\"invalid_surface_rejected\":true,\"gl_error\":0,\"compressed_target_changed_pixels\":"<<changed<<"}\n";
    std::cout<<"Actual font metrics "<<width<<'x'<<height<<"; green glyph pixels "<<green<<'\n';
    }
    context.graphics=nullptr;BindNativeRenderContext(nullptr);
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';BindNativeRenderContext(nullptr);return 1;}}
