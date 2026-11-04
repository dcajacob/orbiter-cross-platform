// Licensed under the MIT License
// The legacy ADI owns a bitmap context; its caller owns the render context.
#pragma once
#include <stdexcept>

namespace dragonfly {
class WglContextRestore {
    HDC dc=wglGetCurrentDC();
    HGLRC context=wglGetCurrentContext();
public:
    WglContextRestore()=default;
    WglContextRestore(HDC targetDC,HGLRC targetContext) {
        if(!targetDC || !targetContext || !wglMakeCurrent(targetDC,targetContext)) {
            wglMakeCurrent(dc,context);
            throw std::runtime_error("Dragonfly ADI context acquisition failed");
        }
    }
    void Discard(HGLRC deleted) {if(context==deleted){dc=nullptr;context=nullptr;}}
    ~WglContextRestore() {
        if(wglGetCurrentDC()!=dc || wglGetCurrentContext()!=context)
            wglMakeCurrent(dc,context);
    }
};
}
