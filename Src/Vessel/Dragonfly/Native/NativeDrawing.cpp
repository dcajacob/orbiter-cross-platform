// Licensed under the MIT License
#include "NativeDrawing.h"
#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <string>
#include <unordered_set>

namespace dragonfly::drawing {
namespace {
std::unordered_set<Object*> objects;
std::unordered_set<Context> contexts;
std::unordered_set<SURFHANDLE> surfaces;
Context active=nullptr;
Font stockFont=nullptr;
Pen stockPen=nullptr;
Brush stockBrush=nullptr;
Bitmap stockBitmap=nullptr;
void require(bool value,const char* message) {if(!value)throw std::runtime_error(message);}
orbiter::production::NativeGraphics& graphics() {
    auto* result=orbiter::production::GetNativeRenderContext().graphics;
    require(result!=nullptr,"Dragonfly native drawing requires the real renderer");return *result;
}
void retain(Object* object) {require(object && objects.count(object),"Invalid Dragonfly drawing resource selection");++object->references;}
void drop(Object* object) {if(object && --object->references==0)delete object;}
void releaseOwner(Object* object) {
    if(!object || !objects.count(object) || !object->owner)return;
    object->owner=false;drop(object);
}
void defaults() {
    if(!stockFont){stockFont=new FontResource(12,"Arial");stockFont->stock=true;}
    if(!stockPen){stockPen=new PenResource(SolidPen,1,Color(0,0,0));stockPen->stock=true;}
    if(!stockBrush){stockBrush=new BrushResource(Color(255,255,255));stockBrush->stock=true;}
    if(!stockBitmap){stockBitmap=new BitmapResource(1,1);stockBitmap->stock=true;}
}
}

Object::Object(Kind value):kind(value) {objects.insert(this);}
Object::~Object() {objects.erase(this);}

BitmapResource::BitmapResource(int w,int h):Object(Kind::Bitmap),width(w),height(h) {
    require(w>0 && h>0,"Invalid Dragonfly native bitmap dimensions");FlushDrawing();
    auto restore=graphics().ActivateMainGraphicsContext();surface=oapiCreateSurface(w,h);
    require(surface!=nullptr,"Dragonfly native bitmap allocation failed");oapiColourFill(surface,Color(0,0,0));
}
BitmapResource::BitmapResource(SURFHANDLE source):Object(Kind::Bitmap),surface(source) {
    require(source && oapiGetSurfaceSize(source,&width,&height),"Invalid Dragonfly native bitmap surface");
    graphics().clbkIncrSurfaceRef(source);
}
BitmapResource::~BitmapResource() {
    if(surface){auto restore=graphics().ActivateMainGraphicsContext();graphics().clbkReleaseSurface(surface);}
}
void BitmapResource::Upload() {
    if(pendingPixels.empty())return;
    FlushDrawing();auto restore=graphics().ActivateMainGraphicsContext();
    require(graphics().UploadSurfacePixels(surface,width,height,pendingPixels),"Dragonfly native instrument bitmap upload failed");
    pendingPixels.clear();
}
void BitmapResource::SetBottomUpPixels(std::vector<std::uint8_t> source) {
    const std::size_t stride=std::size_t(width)*4;
    require(source.size()==stride*std::size_t(height),"Dragonfly original instrument readback dimensions differ");
    pendingPixels.resize(source.size());
    for(int y=0;y<height;++y)std::copy_n(source.data()+std::size_t(height-y-1)*stride,stride,pendingPixels.data()+std::size_t(y)*stride);
    // Original GDI copies RGB and the surface release writes opaque alpha.
    for(std::size_t i=3;i<pendingPixels.size();i+=4)pendingPixels[i]=255;
}
FontResource::FontResource(int height,const char* name):Object(Kind::Font) {
    font=oapiCreateFont(height,true,name,FONT_NORMAL);require(font!=nullptr,"Dragonfly native font allocation failed");
}
FontResource::~FontResource() {if(font)oapiReleaseFont(font);}
PenResource::PenResource(int style,int width,oapi::UInt32 color):Object(Kind::Pen) {
    require(style==SolidPen || style==NullPen,"Unsupported Dragonfly original pen style");
    pen=oapiCreatePen(style==NullPen?0:1,width,color);require(pen!=nullptr,"Dragonfly native pen allocation failed");
}
PenResource::~PenResource() {if(pen)oapiReleasePen(pen);}
BrushResource::BrushResource(oapi::UInt32 value,bool patterned):Object(Kind::Brush),color(value),hatch(patterned) {
    brush=oapiCreateBrush(color);require(brush!=nullptr,"Dragonfly native brush allocation failed");
}
BrushResource::~BrushResource() {if(brush)oapiReleaseBrush(brush);}

struct ContextResource::State {
    Bitmap bitmap=nullptr,originalBitmap=nullptr;
    Font font=nullptr;
    Pen pen=nullptr;
    Brush brush=nullptr;
    oapi::Sketchpad* pad=nullptr;
    std::unique_ptr<orbiter::production::NativeGraphicsContext> restore;
    oapi::UInt32 text=Color(0,0,0),background=Color(255,255,255);
    int alignment=AlignLeft,backgroundMode=Opaque,x=0,y=0;
};
ContextResource::ContextResource(Bitmap bitmap):state(std::make_unique<State>()) {
    defaults();state->bitmap=bitmap?bitmap:stockBitmap;state->font=stockFont;state->pen=stockPen;state->brush=stockBrush;
    state->originalBitmap=state->bitmap;
    retain(state->bitmap);retain(state->originalBitmap);retain(state->font);retain(state->pen);retain(state->brush);contexts.insert(this);
}
ContextResource::~ContextResource() {
    Flush();drop(state->bitmap);drop(state->originalBitmap);drop(state->font);drop(state->pen);drop(state->brush);contexts.erase(this);
}
oapi::Sketchpad* ContextResource::Pad() {
    require(contexts.count(this),"Invalid Dragonfly native drawing context");
    if(active && active!=this)active->Flush();
    if(!state->pad) {
        state->bitmap->Upload();state->restore=graphics().ActivateMainGraphicsContext();
        state->pad=graphics().AcquireRasterSketchpad(state->bitmap->surface);
        require(state->pad!=nullptr,"Dragonfly native bitmap Sketchpad acquisition failed");active=this;
        state->pad->SetFont(state->font->font);state->pad->SetPen(state->pen->pen);state->pad->SetBrush(state->brush->brush);
        state->pad->SetTextColor(state->text);state->pad->SetBackgroundColor(state->background);
        state->pad->SetBackgroundMode(state->backgroundMode==Opaque?oapi::Sketchpad::BK_OPAQUE:oapi::Sketchpad::BK_TRANSPARENT);
        state->pad->SetTextAlign(state->alignment==AlignCenter?oapi::Sketchpad::CENTER:
            state->alignment==AlignRight?oapi::Sketchpad::RIGHT:oapi::Sketchpad::LEFT,oapi::Sketchpad::TOP);
        state->pad->MoveTo(state->x,state->y);
    }
    return state->pad;
}
void ContextResource::Flush() {
    if(state->pad){graphics().ReleaseSketchpadResource(state->pad);state->pad=nullptr;}
    if(active==this)active=nullptr;state->restore.reset();
}
void FlushDrawing() {if(active)active->Flush();}
Module ModuleResources() {static const ResourceModule module;return &module;}
Context CreateCompatibleDC(Context) {return new ContextResource;}
Context GetContext(SURFHANDLE surface) {
    auto* bitmap=new BitmapResource(surface);
    try {auto* result=new ContextResource(bitmap);releaseOwner(bitmap);return result;}
    catch(...){releaseOwner(bitmap);throw;}
}
void ReleaseContext(SURFHANDLE surface,Context context) {
    require(context && contexts.count(context) && context->state->originalBitmap->surface==surface,
            "Dragonfly native surface/context release differs");DeleteDC(context);
}
bool DeleteDC(Context context) {if(!context || !contexts.count(context))return false;delete context;return true;}
bool DeleteObject(Object* object) {
    if(!object || !objects.count(object) || object->stock || !object->owner)return false;
    FlushDrawing();releaseOwner(object);return true;
}
Object* SelectObject(Context context,Object* object) {
    require(context && contexts.count(context) && object && objects.count(object),"Invalid Dragonfly native object selection");
    context->Flush();retain(object);Object* previous=nullptr;
    switch(object->kind) {
    case Kind::Bitmap:previous=context->state->bitmap;context->state->bitmap=static_cast<Bitmap>(object);break;
    case Kind::Font:previous=context->state->font;context->state->font=static_cast<Font>(object);break;
    case Kind::Pen:previous=context->state->pen;context->state->pen=static_cast<Pen>(object);break;
    case Kind::Brush:previous=context->state->brush;context->state->brush=static_cast<Brush>(object);break;
    }
    drop(previous);return previous;
}
Bitmap CreateCompatibleBitmap(Context,int width,int height) {return new BitmapResource(width,height);}
Pen CreatePen(int style,int width,oapi::UInt32 color) {return new PenResource(style,width,color);}
Brush CreateSolidBrush(oapi::UInt32 color) {return new BrushResource(color);}
Brush CreateHatchBrush(int style,oapi::UInt32 color) {
    require(style==BackwardDiagonal,"Unsupported original Dragonfly hatch pattern");return new BrushResource(color,true);
}
Font CreateFont(int height,int width,int escapement,int orientation,int weight,int italic,int underline,int strike,
    int charset,int output,int clip,int quality,int pitch,const char* face) {
    require(width==0 && escapement==0 && orientation==0 && weight==NormalWeight && !italic && !underline && !strike &&
            charset==AnsiCharset && output==RasterPrecision && clip==DefaultClipPrecision && quality==ProofQuality && pitch==DefaultPitch,
            "Original Dragonfly native font request differs");return new FontResource(height,face);
}
std::FILE* OpenResource(const char* name,const char* mode) {
    auto* files=orbiter::production::GetNativeRenderContext().programFiles;
    require(files!=nullptr,"Dragonfly native file resolver unavailable");
    return files->Contains(name)?std::fopen(files->Resolve(name).string().c_str(),mode):nullptr;
}
Bitmap LoadBitmap(Module module,int id) {
    require(module==ModuleResources(),"Dragonfly native resource module identity differs");
    struct ResourceEntry {int id;const char* name;};
    static const ResourceEntry entries[]={
#include "NativeResourceTable.inc"
    };
    const auto item=std::find_if(std::begin(entries),std::end(entries),[id](const auto& value){return value.id==id;});
    require(item!=std::end(entries),"Unknown original Dragonfly bitmap resource");FlushDrawing();
    auto restore=graphics().ActivateMainGraphicsContext();
    const std::string name=std::string("Dragonfly/Panels/")+item->name;
    SURFHANDLE surface=oapiLoadSurfaceEx(name.c_str(),OAPISURFACE_TEXTURE|OAPISURFACE_RENDERTARGET|OAPISURFACE_SKETCHPAD);
    require(surface!=nullptr,"Original Dragonfly native bitmap resource missing");
    try {auto* result=new BitmapResource(surface);graphics().clbkReleaseSurface(surface);return result;}
    catch(...){graphics().clbkReleaseSurface(surface);throw;}
}
SURFHANDLE CreateSurface(int width,int height) {
    FlushDrawing();auto restore=graphics().ActivateMainGraphicsContext();SURFHANDLE result=oapiCreateSurface(width,height);
    require(result!=nullptr,"Dragonfly native drawing surface allocation failed");surfaces.insert(result);return result;
}
SURFHANDLE CreateSurface(Bitmap bitmap,bool release) {
    require(bitmap && objects.count(bitmap),"Invalid original Dragonfly bitmap conversion");FlushDrawing();bitmap->Upload();
    SURFHANDLE result=CreateSurface(bitmap->width,bitmap->height);
    oapiBlt(result,bitmap->surface,0,0,0,0,bitmap->width,bitmap->height);
    if(release)DeleteObject(bitmap);return result;
}
void DestroySurface(SURFHANDLE surface) {
    if(!surface)return;FlushDrawing();
    require(surfaces.erase(surface)==1,"Dragonfly native surface ownership differs");
    auto restore=graphics().ActivateMainGraphicsContext();oapiDestroySurface(surface);
}
void Blt(SURFHANDLE target,SURFHANDLE source,int x,int y,int sx,int sy,int width,int height,oapi::UInt32 key) {
    FlushDrawing();auto restore=graphics().ActivateMainGraphicsContext();oapiBlt(target,source,x,y,sx,sy,width,height,key);
}
void RegisterPanelBackground(Bitmap bitmap,oapi::UInt32 flags,oapi::UInt32 key) {
    SURFHANDLE copy=CreateSurface(bitmap,true);require(surfaces.erase(copy)==1,"Dragonfly background ownership transfer failed");
    oapiRegisterPanelBackground(copy,flags,key);
}
oapi::SdkRectangle Bounds(int left,int top,int right,int bottom) {return {left,top,right,bottom};}
oapi::UInt32 SetTextColor(Context context,oapi::UInt32 color) {const auto old=context->state->text;context->Flush();context->state->text=color;return old;}
oapi::UInt32 SetBkColor(Context context,oapi::UInt32 color) {const auto old=context->state->background;context->Flush();context->state->background=color;return old;}
int SetBkMode(Context context,int mode) {const int old=context->state->backgroundMode;context->Flush();context->state->backgroundMode=mode;return old;}
int SetTextAlign(Context context,int align) {const int old=context->state->alignment;context->Flush();context->state->alignment=align;return old;}
bool TextOut(Context context,int x,int y,const char* text,int length) {return context->Pad()->Text(x,y,text,length);}
bool LineTo(Context context,int x,int y) {context->Pad()->LineTo(x,y);context->state->x=x;context->state->y=y;return true;}
bool MoveToEx(Context context,int x,int y,Point* before) {
    if(before)*before={context->state->x,context->state->y};context->Pad()->MoveTo(x,y);context->state->x=x;context->state->y=y;return true;
}
bool Rectangle(Context context,int left,int top,int right,int bottom) {
    auto* pad=context->Pad();
    if(!context->state->brush->hatch){pad->Rectangle(left,top,right,bottom);return true;}
    // GDI's backward diagonal brush is an eight-pixel device-aligned pattern.
    // Each one-pixel run is submitted to the actual native raster Sketchpad.
    auto* pen=oapiCreatePen(1,1,context->state->brush->color);require(pen!=nullptr,"Dragonfly native hatch pen allocation failed");
    auto* previousPen=pad->SetPen(pen);auto* previousBrush=pad->SetBrush(nullptr);
    for(int y=top;y<bottom;++y)for(int x=left;x<right;++x)if((x+y)%8==0)pad->Line(x,y,x+1,y);
    pad->SetPen(previousPen);pad->SetBrush(previousBrush);oapiReleasePen(pen);
    return true;
}
bool Ellipse(Context context,int left,int top,int right,int bottom) {context->Pad()->Ellipse(left,top,right,bottom);return true;}
bool Polygon(Context context,const Point* points,int count) {
    std::vector<oapi::IVECTOR2> vertices;vertices.reserve(count);
    for(int i=0;i<count;++i)vertices.push_back({points[i].x,points[i].y});
    context->Pad()->Polygon(vertices.data(),count);return true;
}
bool Arc(Context context,int left,int top,int right,int bottom,int startX,int startY,int endX,int endY) {
    const double cx=(left+right)*.5,cy=(top+bottom)*.5,rx=(right-left)*.5,ry=(bottom-top)*.5;
    if(rx<=0 || ry<=0)return false;
    const double start=std::atan2((cy-startY)/ry,(startX-cx)/rx);double end=std::atan2((cy-endY)/ry,(endX-cx)/rx);
    while(end<=start)end+=2*PI;
    const int count=std::max(4,int(std::ceil((end-start)*std::max(rx,ry)*2)));
    std::vector<oapi::IVECTOR2> points;points.reserve(count+1);
    for(int i=0;i<=count;++i){const double a=start+(end-start)*i/count;points.push_back({int(std::lround(cx+rx*std::cos(a))),int(std::lround(cy-ry*std::sin(a)))});}
    context->Pad()->Polyline(points.data(),int(points.size()));return true;
}
bool Pie(Context context,int left,int top,int right,int bottom,int startX,int startY,int endX,int endY) {
    const double cx=(left+right)*.5,cy=(top+bottom)*.5,rx=(right-left)*.5,ry=(bottom-top)*.5;
    if(rx<=0 || ry<=0)return false;
    const double start=std::atan2((cy-startY)/ry,(startX-cx)/rx);double end=std::atan2((cy-endY)/ry,(endX-cx)/rx);
    while(end<=start)end+=2*PI;
    const int count=std::max(4,int(std::ceil((end-start)*std::max(rx,ry)*2)));
    std::vector<oapi::IVECTOR2> points;points.reserve(count+2);points.push_back({int(std::lround(cx)),int(std::lround(cy))});
    for(int i=0;i<=count;++i){const double a=start+(end-start)*i/count;points.push_back({int(std::lround(cx+rx*std::cos(a))),int(std::lround(cy-ry*std::sin(a)))});}
    context->Pad()->Polygon(points.data(),int(points.size()));return true;
}
bool BitBlt(Context target,int x,int y,int width,int height,Context source,int sx,int sy,std::uint32_t operation) {
    require(operation==CopyPixels,"Unsupported original Dragonfly bitmap raster operation");FlushDrawing();
    source->state->bitmap->Upload();target->state->bitmap->Upload();
    oapiBlt(target->state->bitmap->surface,source->state->bitmap->surface,x,y,sx,sy,width,height);return true;
}
void ReleaseStockResources() {
    FlushDrawing();while(!contexts.empty())DeleteDC(*contexts.begin());
    stockFont=nullptr;stockPen=nullptr;stockBrush=nullptr;stockBitmap=nullptr;
    const std::vector<Object*> remaining(objects.begin(),objects.end());for(auto* object:remaining)releaseOwner(object);
    require(objects.empty(),"Dragonfly native drawing selection lifetime remains active at module release");
    while(!surfaces.empty())DestroySurface(*surfaces.begin());
}
}
