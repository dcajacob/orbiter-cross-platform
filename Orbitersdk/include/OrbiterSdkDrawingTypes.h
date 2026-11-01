// Licensed under the MIT License
#ifndef ORBITER_SDK_DRAWING_TYPES_H
#define ORBITER_SDK_DRAWING_TYPES_H
#include <cstdint>
#ifdef _WIN32
#include <windows.h>
#endif
namespace oapi {
#ifdef _WIN32
using SdkRectangle=RECT;
using SdkDrawContext=HDC;
#else
struct SdkRectangle {std::int32_t left,top,right,bottom;};
// Native clients must port GDI drawing to Sketchpad. This opaque context is an
// SDK drawing resource, not a simulated Windows device context or GDI API.
class SdkDrawingContext;
using SdkDrawContext=SdkDrawingContext*;
#endif
}
#endif
