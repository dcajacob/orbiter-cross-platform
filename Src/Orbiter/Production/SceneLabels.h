// Licensed under the MIT License
#ifndef ORBITER_PRODUCTION_SCENE_LABELS_H
#define ORBITER_PRODUCTION_SCENE_LABELS_H
#include "CoreTypes.h"
#include "OrbiterVector.h"
#include <string>
#include <vector>
#ifdef _WIN32
#include "GraphicsAPI.h"
#endif
namespace orbiter::production {
#ifdef _WIN32
// Preserve the actual nested SDK type identities and Windows method mangling.
using SceneLabel = oapi::GraphicsClient::LABELSPEC;
using SceneLabelList = oapi::GraphicsClient::LABELLIST;
using SceneLabelType = oapi::GraphicsClient::LABELTYPE;
#else
// Internal native records; renderer adapters do not replace SDK/numerical types.
struct SceneLabel { VECTOR3 pos; std::string label[2]; };
struct SceneLabelList {
    std::string name;
    std::vector<SceneLabel> marker;
    int colour;
    int shape;
    float size;
    float distfac;
    UInt32 flag;
    bool active;
};
struct SceneLabelType {
    char labelId;
    char markerId;
    UInt32 col;
    char* name;
    bool active;
};
#endif
}
#endif
