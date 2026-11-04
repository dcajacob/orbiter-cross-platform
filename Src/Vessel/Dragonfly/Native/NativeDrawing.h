// Licensed under the MIT License
// Private native drawing resources for the original Dragonfly source. The
// Windows module keeps its actual SDK/GDI types and implementation unchanged.
#pragma once
#include "../../StockVesselPlatform.h"
#include "Production/NativeGraphics.h"
#include <cstdint>
#include <cstdio>
#include <memory>
#include <vector>

namespace dragonfly {class InstrumentTarget;}
namespace dragonfly::drawing {
enum class Kind {Bitmap,Font,Pen,Brush};
class Object {
public:
    const Kind kind;
    unsigned references=1;
    bool stock=false,owner=true;
    explicit Object(Kind);
    virtual ~Object();
};
class BitmapResource final:public Object {
public:
    SURFHANDLE surface=nullptr;
    int width=0,height=0;
    std::vector<std::uint8_t> pendingPixels;
    BitmapResource(int,int);
    explicit BitmapResource(SURFHANDLE);
    ~BitmapResource() override;
    void Upload();
    void SetBottomUpPixels(std::vector<std::uint8_t>);
};
class FontResource final:public Object {
public:
    oapi::Font* font=nullptr;
    FontResource(int,const char*);
    ~FontResource() override;
};
class PenResource final:public Object {
public:
    oapi::Pen* pen=nullptr;
    PenResource(int,int,oapi::UInt32);
    ~PenResource() override;
};
class BrushResource final:public Object {
public:
    oapi::Brush* brush=nullptr;
    oapi::UInt32 color;
    bool hatch=false;
    BrushResource(oapi::UInt32,bool=false);
    ~BrushResource() override;
};
class ContextResource {
public:
    struct State;
    std::unique_ptr<State> state;
    explicit ContextResource(BitmapResource* = nullptr);
    ~ContextResource();
    oapi::Sketchpad* Pad();
    void Flush();
};
using Context=ContextResource*;
using Bitmap=BitmapResource*;
using Font=FontResource*;
using Pen=PenResource*;
using Brush=BrushResource*;
struct ResourceModule {};
using Module=const ResourceModule*;
using Point=oapi::SdkPoint;
using GlContext=dragonfly::InstrumentTarget*;

// These are the actual on-disk BMP record layouts used by the original ADI
// reader, independent of compiler/platform integer and structure padding.
#pragma pack(push,2)
struct BitmapFileHeader {
    std::uint16_t bfType;
    std::uint32_t bfSize;
    std::uint16_t bfReserved1,bfReserved2;
    std::uint32_t bfOffBits;
};
#pragma pack(pop)
struct BitmapInfoHeader {
    std::uint32_t biSize;
    std::int32_t biWidth,biHeight;
    std::uint16_t biPlanes,biBitCount;
    std::uint32_t biCompression,biSizeImage;
    std::int32_t biXPelsPerMeter,biYPelsPerMeter;
    std::uint32_t biClrUsed,biClrImportant;
};
struct RgbTriple {std::uint8_t rgbtBlue,rgbtGreen,rgbtRed;};
static_assert(sizeof(BitmapFileHeader)==14 && sizeof(BitmapInfoHeader)==40 && sizeof(RgbTriple)==3);

constexpr int SolidPen=0,NullPen=5,BackwardDiagonal=3;
constexpr int AlignLeft=0,AlignRight=2,AlignCenter=6,Opaque=2,Transparent=1;
constexpr int NormalWeight=400,AnsiCharset=0,RasterPrecision=1,DefaultClipPrecision=0,ProofQuality=2,DefaultPitch=0;
constexpr std::uint32_t CopyPixels=0x00CC0020;
constexpr oapi::UInt32 Color(unsigned r,unsigned g,unsigned b) {return r|(g<<8)|(b<<16);}
constexpr int Resource(int id) {return id;}

Module ModuleResources();
void ReleaseStockResources();
void FlushDrawing();
std::FILE* OpenResource(const char*,const char*);
Bitmap LoadBitmap(Module,int);
Bitmap CreateCompatibleBitmap(Context,int,int);
Context CreateCompatibleDC(Context);
Context GetContext(SURFHANDLE);
void ReleaseContext(SURFHANDLE,Context);
bool DeleteDC(Context);
bool DeleteObject(Object*);
Object* SelectObject(Context,Object*);
Pen CreatePen(int,int,oapi::UInt32);
Brush CreateSolidBrush(oapi::UInt32);
Brush CreateHatchBrush(int,oapi::UInt32);
Font CreateFont(int,int,int,int,int,int,int,int,int,int,int,int,int,const char*);
SURFHANDLE CreateSurface(int,int);
SURFHANDLE CreateSurface(Bitmap,bool=true);
void DestroySurface(SURFHANDLE);
void Blt(SURFHANDLE,SURFHANDLE,int,int,int,int,int,int,oapi::UInt32=SURF_NO_CK);
void RegisterPanelBackground(Bitmap,oapi::UInt32=PANEL_ATTACH_BOTTOM|PANEL_MOVEOUT_BOTTOM,oapi::UInt32=oapi::UInt32(-1));
oapi::SdkRectangle Bounds(int,int,int,int);
oapi::UInt32 SetTextColor(Context,oapi::UInt32);
oapi::UInt32 SetBkColor(Context,oapi::UInt32);
int SetBkMode(Context,int);
int SetTextAlign(Context,int);
bool TextOut(Context,int,int,const char*,int);
bool LineTo(Context,int,int);
bool MoveToEx(Context,int,int,Point*);
bool Rectangle(Context,int,int,int,int);
bool Ellipse(Context,int,int,int,int);
bool Arc(Context,int,int,int,int,int,int,int,int);
bool Pie(Context,int,int,int,int,int,int,int,int);
bool Polygon(Context,const Point*,int);
bool BitBlt(Context,int,int,int,int,Context,int,int,std::uint32_t);
}
