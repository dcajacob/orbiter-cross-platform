// Renderer-private conversions; never assume SDK/GPU structure layout equality.
#pragma once
#include "OGLClient.h"
inline OGLMaterial ToRendererMaterial(const MATERIAL &m) {
    return {{m.diffuse.r,m.diffuse.g,m.diffuse.b,m.diffuse.a},
            {m.ambient.r,m.ambient.g,m.ambient.b,m.ambient.a},
            {m.specular.r,m.specular.g,m.specular.b,m.specular.a},
            {m.emissive.r,m.emissive.g,m.emissive.b,m.emissive.a},m.power};
}
inline MATERIAL ToSdkMaterial(const OGLMaterial &m) {
    MATERIAL out{};
    out.diffuse={m.diffuse.r,m.diffuse.g,m.diffuse.b,m.diffuse.a};
    out.ambient={m.ambient.r,m.ambient.g,m.ambient.b,m.ambient.a};
    out.specular={m.specular.r,m.specular.g,m.specular.b,m.specular.a};
    out.emissive={m.emissive.r,m.emissive.g,m.emissive.b,m.emissive.a};
    out.power=m.specular_power;return out;
}
