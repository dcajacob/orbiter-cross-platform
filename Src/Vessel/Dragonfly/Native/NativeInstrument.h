// Licensed under the MIT License
#pragma once
#include "NativeDrawing.h"
#include <stdexcept>
#include <utility>

namespace dragonfly {
class InstrumentTarget {
    drawing::Bitmap bitmap=nullptr;
    drawing::Context context=nullptr;
    drawing::Object* previous=nullptr;
    std::unique_ptr<orbiter::production::NativeInstrumentTarget> target;
    void ReleaseBitmap() {
        auto restore=orbiter::production::GetNativeRenderContext().graphics->ActivateMainGraphicsContext();
        if(context){drawing::DeleteDC(context);context=nullptr;}
        if(bitmap){drawing::DeleteObject(bitmap);bitmap=nullptr;}
    }
public:
    InstrumentTarget(int width,int height) {
        drawing::FlushDrawing();
        try {
            bitmap=drawing::CreateCompatibleBitmap(nullptr,width,height);
            context=drawing::CreateCompatibleDC(nullptr);previous=drawing::SelectObject(context,bitmap);
            target=orbiter::production::GetNativeRenderContext().graphics->CreateInstrumentTarget(width,height);
        } catch(...) {ReleaseBitmap();throw;}
    }
    ~InstrumentTarget() {ReleaseBitmap();target.reset();}
    InstrumentTarget(const InstrumentTarget&)=delete;
    InstrumentTarget& operator=(const InstrumentTarget&)=delete;
    drawing::Context BitmapDC() const {return context;}
    InstrumentTarget* RenderDC() {return this;}
    InstrumentTarget* Context() {return this;}
    drawing::Bitmap Bitmap() const {return bitmap;}
    drawing::Object* PreviousBitmap() const {return previous;}
    void Activate() {drawing::FlushDrawing();target->Activate();}
    void Readback() {
        std::vector<std::uint8_t> pixels;target->Readback(pixels);bitmap->SetBottomUpPixels(std::move(pixels));
    }
};

class InstrumentContextRestore {
    std::unique_ptr<orbiter::production::NativeGraphicsContext> saved;
public:
    InstrumentContextRestore() {
        drawing::FlushDrawing();saved=orbiter::production::GetNativeRenderContext().graphics->SaveGraphicsContext();
    }
    InstrumentContextRestore(InstrumentTarget* target,InstrumentTarget* context):InstrumentContextRestore() {
        if(!target || target!=context)throw std::runtime_error("Native Dragonfly instrument context identity differs");
        target->Activate();
    }
};
}
