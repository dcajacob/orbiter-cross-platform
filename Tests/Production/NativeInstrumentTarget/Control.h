// Licensed under the MIT License
// Opt-in graphics control in a real scene; no vessel/clock/camera setter is used.
#pragma once
#define GL_GLEXT_PROTOTYPES 1
#include <GL/gl.h>
#include <GL/glext.h>
#include "Production/NativeGraphics.h"
#include <array>
#include <fstream>
#include <stdexcept>
#include <vector>

namespace native_instrument_target {
inline void require(bool value,const char* message) {if(!value)throw std::runtime_error(message);}
inline void clean(const char* message) {require(glGetError()==GL_NO_ERROR,message);}

constexpr GLenum pixelParameters[]={GL_PACK_ALIGNMENT,GL_PACK_ROW_LENGTH,GL_PACK_SKIP_PIXELS,GL_PACK_SKIP_ROWS,
    GL_PACK_IMAGE_HEIGHT,GL_PACK_SKIP_IMAGES,GL_PACK_SWAP_BYTES,GL_PACK_LSB_FIRST,
    GL_UNPACK_ALIGNMENT,GL_UNPACK_ROW_LENGTH,GL_UNPACK_SKIP_PIXELS,GL_UNPACK_SKIP_ROWS,
    GL_UNPACK_IMAGE_HEIGHT,GL_UNPACK_SKIP_IMAGES,GL_UNPACK_SWAP_BYTES,GL_UNPACK_LSB_FIRST};
struct State {
    std::array<GLint,16> pixels{};
    GLint active=0,texture0=0,texture3=0,pack=0,unpack=0,draw=0,read=0,program=0,vao=0,profile=0;
    State() {
        for(unsigned i=0;i<16;++i)glGetIntegerv(pixelParameters[i],&pixels[i]);
        glGetIntegerv(GL_ACTIVE_TEXTURE,&active);
        glActiveTexture(GL_TEXTURE0);glGetIntegerv(GL_TEXTURE_BINDING_2D,&texture0);
        glActiveTexture(GL_TEXTURE3);glGetIntegerv(GL_TEXTURE_BINDING_2D,&texture3);glActiveTexture(active);
        glGetIntegerv(GL_PIXEL_PACK_BUFFER_BINDING,&pack);glGetIntegerv(GL_PIXEL_UNPACK_BUFFER_BINDING,&unpack);
        glGetIntegerv(GL_DRAW_FRAMEBUFFER_BINDING,&draw);glGetIntegerv(GL_READ_FRAMEBUFFER_BINDING,&read);
        glGetIntegerv(GL_CURRENT_PROGRAM,&program);glGetIntegerv(GL_VERTEX_ARRAY_BINDING,&vao);
        glGetIntegerv(GL_CONTEXT_PROFILE_MASK,&profile);clean("Instrument control state query failed");
    }
    bool operator==(const State& b) const {
        return pixels==b.pixels && active==b.active && texture0==b.texture0 && texture3==b.texture3 &&
            pack==b.pack && unpack==b.unpack && draw==b.draw && read==b.read && program==b.program && vao==b.vao && profile==b.profile;
    }
    void RestorePixelState() const {
        for(unsigned i=0;i<16;++i)glPixelStorei(pixelParameters[i],pixels[i]);
        glBindBuffer(GL_PIXEL_PACK_BUFFER,pack);glBindBuffer(GL_PIXEL_UNPACK_BUFFER,unpack);
        glActiveTexture(GL_TEXTURE0);glBindTexture(GL_TEXTURE_2D,texture0);
        glActiveTexture(GL_TEXTURE3);glBindTexture(GL_TEXTURE_2D,texture3);glActiveTexture(active);
    }
};

inline void run() {
    auto* graphics=orbiter::production::GetNativeRenderContext().graphics;
    require(graphics!=nullptr,"Native instrument control requires actual renderer");
    const State main;
    require(main.profile&GL_CONTEXT_CORE_PROFILE_BIT,"Actual main renderer is not a core context");
    unsigned pixelsChecked=0,contexts=0,restorations=0,uploads=0;
    bool collision=false;
    for(const auto size:std::array<std::array<int,2>,2>{{{13,7},{160,160}}}) {
        const int width=size[0],height=size[1];
        auto target=graphics->CreateInstrumentTarget(width,height);++contexts;
        require(State()==main,"Instrument construction changed actual main context/state");++restorations;
        {
            auto restore=graphics->SaveGraphicsContext();target->Activate();
            GLint profile=0,depth=-1,stencil=-1,type=0;
            glGetIntegerv(GL_CONTEXT_PROFILE_MASK,&profile);glGetIntegerv(GL_DEPTH_BITS,&depth);glGetIntegerv(GL_STENCIL_BITS,&stencil);
            glGetFramebufferAttachmentParameteriv(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_FRAMEBUFFER_ATTACHMENT_OBJECT_TYPE,&type);
            require(profile&GL_CONTEXT_COMPATIBILITY_PROFILE_BIT,"Instrument context lacks original compatibility operations");
            require(depth==0 && stencil==0 && type==GL_RENDERBUFFER,"Instrument framebuffer differs from original zero-depth/stencil request or aliases a texture");
            // Reproduce the earlier texture-target allocation sequence. Binding
            // the ADI's real texture name and dimensions resizes that attachment.
            if(!collision) {
                GLuint framebuffer=0;glGenFramebuffers(1,&framebuffer);glBindFramebuffer(GL_FRAMEBUFFER,framebuffer);
                glBindTexture(GL_TEXTURE_2D,1);glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA8,width,height,0,GL_RGBA,GL_UNSIGNED_BYTE,nullptr);
                glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,1,0);
                GLint before=0,after=0;glGetTexLevelParameteriv(GL_TEXTURE_2D,0,GL_TEXTURE_WIDTH,&before);
                glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA8,512,256,0,GL_RGBA,GL_UNSIGNED_BYTE,nullptr);
                glGetTexLevelParameteriv(GL_TEXTURE_2D,0,GL_TEXTURE_WIDTH,&after);
                require(before==width && after==512,"Earlier texture attachment collision did not reproduce");
                collision=true;glDeleteFramebuffers(1,&framebuffer);target->Activate();
            }
            std::vector<std::uint8_t> image(std::size_t(512)*256*4);
            for(std::size_t i=0;i<image.size();i+=4){image[i]=0;image[i+1]=255;image[i+2]=0;image[i+3]=255;}
            glBindTexture(GL_TEXTURE_2D,1);glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA8,512,256,0,GL_RGBA,GL_UNSIGNED_BYTE,image.data());
            glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
            glViewport(0,0,width,height);glClearColor(0,0,1,1);glClear(GL_COLOR_BUFFER_BIT);
            glMatrixMode(GL_PROJECTION);glLoadIdentity();glOrtho(0,width,0,height,-1,1);
            glMatrixMode(GL_MODELVIEW);glLoadIdentity();glDisable(GL_LIGHTING);glDisable(GL_DEPTH_TEST);
            glEnable(GL_TEXTURE_2D);glTexEnvi(GL_TEXTURE_ENV,GL_TEXTURE_ENV_MODE,GL_REPLACE);
            const GLfloat vertices[]={0,0,0, GLfloat(width),0,0, 0,GLfloat(height),0, GLfloat(width),GLfloat(height),0};
            const GLfloat coordinates[]={0,0,1,0,0,1,1,1};const GLuint indices[]={0,1,2,3};
            glEnableClientState(GL_VERTEX_ARRAY);glEnableClientState(GL_TEXTURE_COORD_ARRAY);
            glVertexPointer(3,GL_FLOAT,0,vertices);glTexCoordPointer(2,GL_FLOAT,0,coordinates);
            const GLuint list=glGenLists(1);require(list!=0,"Actual original-style compatibility display list failed");
            glNewList(list,GL_COMPILE);glDrawElements(GL_TRIANGLE_STRIP,4,GL_UNSIGNED_INT,indices);glEndList();
            glCallList(list);glFinish();clean("Original-style textured compatibility drawing failed");
            GLuint pack=0;glGenBuffers(1,&pack);glBindBuffer(GL_PIXEL_PACK_BUFFER,pack);glBufferData(GL_PIXEL_PACK_BUFFER,4096,nullptr,GL_STREAM_READ);
            glPixelStorei(GL_PACK_ALIGNMENT,8);glPixelStorei(GL_PACK_ROW_LENGTH,width+7);glPixelStorei(GL_PACK_SKIP_PIXELS,3);
            glPixelStorei(GL_PACK_SKIP_ROWS,2);glPixelStorei(GL_PACK_IMAGE_HEIGHT,height+5);glPixelStorei(GL_PACK_SKIP_IMAGES,1);
            glPixelStorei(GL_PACK_SWAP_BYTES,1);glPixelStorei(GL_PACK_LSB_FIRST,1);glActiveTexture(GL_TEXTURE3);
            const State packed;std::vector<std::uint8_t> pixels;target->Readback(pixels);
            require(State()==packed,"Instrument readback failed to restore nondefault pixel/buffer/texture state");
            require(pixels.size()==std::size_t(width)*height*4,"Actual instrument readback dimensions differ");
            for(std::size_t i=0;i<pixels.size();i+=4) {
                require(pixels[i]==0 && pixels[i+1]==255 && pixels[i+2]==0 && pixels[i+3]==255,"Texture name 1 corrupted actual instrument color storage");++pixelsChecked;
            }
            std::ofstream output("instrument-"+std::to_string(width)+"x"+std::to_string(height)+".rgba",std::ios::binary);
            output.write(reinterpret_cast<const char*>(pixels.data()),pixels.size());
            glDeleteBuffers(1,&pack);glDeleteLists(list,1);const GLuint texture=1;glDeleteTextures(1,&texture);
        }
        require(State()==main,"Instrument scope failed to restore actual main context/state");++restorations;
        target.reset();require(State()==main,"Instrument destruction changed actual main context/state");++restorations;
    }
    {
        auto restore=graphics->SaveGraphicsContext();auto target=graphics->CreateInstrumentTarget(11,9);++contexts;
        target->Activate();target.reset();
    }
    require(State()==main,"Destroying the currently active instrument failed to restore main context");++restorations;
    {
        const State saved;const int width=9,height=5;SURFHANDLE surface=graphics->CreateSurfaceResource(width,height);
        require(surface!=nullptr,"Actual pixel-upload control surface creation failed");
        std::vector<std::uint8_t> expected(std::size_t(width)*height*4),actual(expected.size());
        for(int y=0;y<height;++y)for(int x=0;x<width;++x) {
            const auto i=(std::size_t(y)*width+x)*4;expected[i]=x*23;expected[i+1]=y*47;expected[i+2]=x+y;expected[i+3]=255;
        }
        GLuint unpack=0,foreign=0;glGenBuffers(1,&unpack);glBindBuffer(GL_PIXEL_UNPACK_BUFFER,unpack);glBufferData(GL_PIXEL_UNPACK_BUFFER,4096,nullptr,GL_STREAM_DRAW);
        glGenTextures(1,&foreign);glActiveTexture(GL_TEXTURE3);glBindTexture(GL_TEXTURE_2D,foreign);
        glPixelStorei(GL_UNPACK_ALIGNMENT,8);glPixelStorei(GL_UNPACK_ROW_LENGTH,19);glPixelStorei(GL_UNPACK_SKIP_PIXELS,3);
        glPixelStorei(GL_UNPACK_SKIP_ROWS,2);glPixelStorei(GL_UNPACK_IMAGE_HEIGHT,33);glPixelStorei(GL_UNPACK_SKIP_IMAGES,1);
        glPixelStorei(GL_UNPACK_SWAP_BYTES,1);glPixelStorei(GL_UNPACK_LSB_FIRST,1);
        const State nondefault;require(graphics->UploadSurfacePixels(surface,width,height,expected),"Actual renderer pixel upload failed");++uploads;
        require(State()==nondefault,"Native pixel upload changed nondefault transfer/buffer/texture state");
        saved.RestorePixelState();
        glBindBuffer(GL_PIXEL_PACK_BUFFER,0);for(unsigned i=0;i<8;++i)glPixelStorei(pixelParameters[i],i?0:1);
        glActiveTexture(GL_TEXTURE0);glBindTexture(GL_TEXTURE_2D,GLuint(graphics->GuiTextureId(surface)));
        glGetTexImage(GL_TEXTURE_2D,0,GL_RGBA,GL_UNSIGNED_BYTE,actual.data());clean("Actual uploaded-surface readback failed");
        require(actual==expected,"Actual uploaded-surface bytes differ or reverse rows");pixelsChecked+=width*height;
        saved.RestorePixelState();glDeleteBuffers(1,&unpack);glDeleteTextures(1,&foreign);graphics->ReleaseTextureResource(surface);
        require(State()==saved,"Pixel upload control failed to release its real resources/state");
    }
    require(State()==main && collision,"Native instrument control did not restore ordinary scene state");clean("Native instrument control OpenGL diagnostic");
    std::ofstream result("native-instrument-control.json");
    result<<"{\"status\":\"passed\",\"contexts\":"<<contexts<<",\"context_restorations\":"<<restorations
          <<",\"display_lists\":2,\"pixel_uploads\":"<<uploads<<",\"checked_pixels\":"<<pixelsChecked
          <<",\"texture_name_1_collision_reproduced\":true,\"native_admission_qualified\":false,\"phase6_complete\":false}\n";
}
}
