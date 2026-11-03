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
    void PlaybackNote(char* event);
    void EndPlayback();
    void Render();
    void Clear();
private:
    std::unique_ptr<oapi::ScreenAnnotation> playback;
    std::vector<std::unique_ptr<oapi::ScreenAnnotation>> notes;
};
}
