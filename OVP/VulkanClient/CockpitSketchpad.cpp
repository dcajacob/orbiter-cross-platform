// Licensed under the MIT License
#include "CockpitSketchpad.h"
#include "CockpitFontData.h"
#include <algorithm>
#include <cmath>
#include <cstring>
#include <utility>

namespace orbiter::vulkan {
namespace {
class Pad final : public oapi::Sketchpad {
public:
    Pad(SURFHANDLE handle, TextureData& image) : Sketchpad(handle),
        surface_(SDL_CreateSurfaceFrom(image.width, image.height, SDL_PIXELFORMAT_RGBA32,
            image.pixels.data(), int(image.width)*4), SDL_DestroySurface),
        renderer_(surface_ ? SDL_CreateSoftwareRenderer(surface_.get()) : nullptr, SDL_DestroyRenderer)
    {
        Require(bool(renderer_), "Open cockpit instrument drawing surface");
    }
    ~Pad() override { SDL_FlushRenderer(renderer_.get()); }
    oapi::Pen* SetPen(oapi::Pen* pen) override { return std::exchange(pen_, static_cast<CockpitPen*>(pen)); }
    oapi::Brush* SetBrush(oapi::Brush* brush) override { return std::exchange(brush_, static_cast<CockpitBrush*>(brush)); }
    oapi::Font* SetFont(oapi::Font* font) override { return std::exchange(font_, static_cast<CockpitFont*>(font)); }
    void SetTextAlign(TAlign_horizontal h, TAlign_vertical v) override { horizontal_ = h; vertical_ = v; }
    oapi::UInt32 SetTextColor(oapi::UInt32 c) override { return std::exchange(text_,c); }
    oapi::UInt32 SetBackgroundColor(oapi::UInt32 c) override { return std::exchange(background_,c); }
    void SetBackgroundMode(BkgMode mode) override { backgroundMode_ = mode; }
    void SetOrigin(int x, int y) override { ox_=x; oy_=y; }
    void GetOrigin(int* x, int* y) const override { *x=ox_; *y=oy_; }
    oapi::UInt32 GetCharSize() override { return (charWidth()<<16) | charHeight(); }
    oapi::UInt32 GetTextWidth(const char* s, int n) override {
        return s ? charWidth()*(n>0 ? size_t(n) : std::strlen(s)) : 0;
    }
    bool Text(int x, int y, const char* s, int n) override {
        if (!s) return false;
        std::string text(s,n>0 ? size_t(n) : std::strlen(s));
        const int w=charWidth(), h=charHeight(), length=w*int(text.size());
        x+=ox_; y+=oy_;
        if (horizontal_==CENTER) x-=length/2;
        if (horizontal_==RIGHT) x-=length;
        if (vertical_==BOTTOM) y-=h;
        if (vertical_==BASELINE) y-=h*7/8;
        if (backgroundMode_==BK_OPAQUE) {
            color(background_);
            const SDL_FRect box{float(x),float(y),float(length),float(h)};
            SDL_RenderFillRect(renderer_.get(), &box);
        }
        // Keep vector and text operations in call order when the software
        // renderer buffers lines. Each font owns its antialiased, sized atlas.
        SDL_FlushRenderer(renderer_.get());
        auto& font = font_ ? *font_ : fallback_;
        if (!font.atlas) {
            static const std::unique_ptr<SDL_Surface,decltype(&SDL_DestroySurface)> master(
                SDL_LoadPNG_IO(SDL_IOFromConstMem(cockpitFontPng,sizeof(cockpitFontPng)),true),SDL_DestroySurface);
            if (!master) return false;
            font.atlas.reset(SDL_ScaleSurface(master.get(),16*w,6*h,SDL_SCALEMODE_LINEAR));
            if (!font.atlas) return false;
            SDL_SetSurfaceBlendMode(font.atlas.get(),SDL_BLENDMODE_BLEND);
        }
        SDL_SetSurfaceColorMod(font.atlas.get(),Uint8(text_),Uint8(text_>>8),Uint8(text_>>16));
        for (unsigned char c : text) {
            const unsigned glyph = c>=32 && c<=126 ? c-32 : '?'-32;
            SDL_Rect src{int(glyph%16)*w,int(glyph/16)*h,w,h}, dst{x,y,w,h};
            if (!SDL_BlitSurface(font.atlas.get(),&src,surface_.get(),&dst)) return false;
            x+=w;
        }
        return true;
    }
    void Pixel(int x,int y,oapi::UInt32 c) override { color(c); SDL_RenderPoint(renderer_.get(),float(x+ox_),float(y+oy_)); }
    void MoveTo(int x,int y) override { x_=x; y_=y; }
    void LineTo(int x,int y) override { Line(x_,y_,x,y); MoveTo(x,y); }
    void Line(int ax,int ay,int bx,int by) override {
        MoveTo(bx,by);
        if (!pen_ || !pen_->style) return;
        color(pen_->color);
        const bool steep=std::abs(by-ay)>std::abs(bx-ax);
        for(int i=0;i<pen_->width;++i) {
            const int dx=ox_+(steep ? i-pen_->width/2 : 0), dy=oy_+(steep ? 0 : i-pen_->width/2);
            SDL_RenderLine(renderer_.get(),float(ax+dx),float(ay+dy),float(bx+dx),float(by+dy));
        }
    }
    void Rectangle(int x0,int y0,int x1,int y1) override {
        if (brush_) {
            color(brush_->color);
            const SDL_FRect box{float(ox_+x0),float(oy_+y0),float(x1-x0),float(y1-y0)};
            SDL_RenderFillRect(renderer_.get(),&box);
        }
        Line(x0,y0,x1,y0); Line(x1,y0,x1,y1); Line(x1,y1,x0,y1); Line(x0,y1,x0,y0);
    }
    void Ellipse(int x0,int y0,int x1,int y1) override {
        const double rx=(x1-x0)*0.5, ry=(y1-y0)*0.5;
        const auto n=std::clamp(int(std::max(std::abs(rx),std::abs(ry))*2),12,180);
        std::vector<oapi::IVECTOR2> points(n);
        for(int j=0;j<n;++j) {
            const double a=6.283185307179586*j/n;
            points[j]={int(std::lround(x0+rx*(1+std::cos(a)))),int(std::lround(y0+ry*(1+std::sin(a))))};
        }
        Polygon(points.data(),n);
    }
    void Polyline(const oapi::IVECTOR2* p,int n) override {
        for(int i=1;i<n;++i) Line(p[i-1].x,p[i-1].y,p[i].x,p[i].y);
    }
    void Polygon(const oapi::IVECTOR2* p,int n) override {
        if(n<2) return;
        if(brush_) {
            const auto bounds=std::minmax_element(p,p+n,[](const auto& a,const auto& b){return a.y<b.y;});
            std::vector<float> crossings;
            color(brush_->color);
            const int first = std::max(-oy_, int(bounds.first->y));
            const int last = std::min(surface_->h-oy_, int(bounds.second->y));
            for(int y=first; y<last; ++y) {
                crossings.clear();
                for(int i=0,j=n-1;i<n;j=i++) {
                    if ((p[i].y>y)==(p[j].y>y)) continue;
                    crossings.push_back(float(p[i].x)+float(y-p[i].y)*(p[j].x-p[i].x)/(p[j].y-p[i].y));
                }
                std::sort(crossings.begin(),crossings.end());
                for(size_t i=1;i<crossings.size();i+=2)
                    SDL_RenderLine(renderer_.get(),ox_+crossings[i-1],float(oy_+y),ox_+crossings[i],float(oy_+y));
            }
        }
        Polyline(p,n); Line(p[n-1].x,p[n-1].y,p[0].x,p[0].y);
    }
private:
    void color(oapi::UInt32 c) { SDL_SetRenderDrawColor(renderer_.get(),Uint8(c),Uint8(c>>8),Uint8(c>>16),255); }
    int charHeight() const { return font_ ? font_->height : 12; }
    int charWidth() const { return std::max(1,int(std::lround(charHeight()*0.60))); }
    std::unique_ptr<SDL_Surface,decltype(&SDL_DestroySurface)> surface_;
    std::unique_ptr<SDL_Renderer,decltype(&SDL_DestroyRenderer)> renderer_;
    CockpitFont fallback_{12,false,"Fixed",FontStyle::FONT_NORMAL,0};
    CockpitPen* pen_=nullptr;
    CockpitBrush* brush_=nullptr;
    CockpitFont* font_=nullptr;
    oapi::UInt32 text_=0xffffff, background_=0;
    BkgMode backgroundMode_=BK_TRANSPARENT;
    TAlign_horizontal horizontal_=LEFT;
    TAlign_vertical vertical_=TOP;
    int x_=0,y_=0,ox_=0,oy_=0;
};
} // namespace
oapi::Sketchpad* OpenCockpitSketchpad(OrbiterScene& scene,SURFHANDLE handle)
{
    auto* image=scene.Writable(handle);
    return image ? new Pad(handle,*image) : nullptr;
}
} // namespace orbiter::vulkan
