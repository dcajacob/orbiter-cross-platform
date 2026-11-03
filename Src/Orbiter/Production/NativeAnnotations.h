// Licensed under the MIT License
#pragma once
#include "NativeGraphics.h"
#include <memory>

namespace oapi {class ScreenAnnotation;}
namespace orbiter::production {
class NativeAnnotations {
public:
    NativeAnnotations();
    ~NativeAnnotations();
    NOTEHANDLE Create(double size,const VECTOR3 &col);
    bool Remove(NOTEHANDLE handle);
    void Render();
    void Clear();
private:
    std::vector<std::unique_ptr<oapi::ScreenAnnotation>> notes;
};
}
