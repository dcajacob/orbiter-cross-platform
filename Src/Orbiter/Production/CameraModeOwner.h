// Licensed under the MIT License
#pragma once
#include <memory>
#include "CamAPI.h"

namespace orbiter::production {
// The public CameraMode ABI has no virtual destructor. The engine's factory
// and preset list own exactly these three concrete SDK types.
struct DeleteCameraMode {
    void operator()(CameraMode* mode) const noexcept {
        if(!mode)return;
        switch(mode->GetMode()) {
        case CameraMode::CM_COCKPIT:delete static_cast<CameraMode_Cockpit*>(mode);break;
        case CameraMode::CM_TRACK:delete static_cast<CameraMode_Track*>(mode);break;
        case CameraMode::CM_GROUND:delete static_cast<CameraMode_Ground*>(mode);break;
        }
    }
};
using OwnedCameraMode=std::unique_ptr<CameraMode,DeleteCameraMode>;
}
