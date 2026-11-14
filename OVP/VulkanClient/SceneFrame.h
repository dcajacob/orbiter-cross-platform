// Licensed under the MIT License
#pragma once

#ifdef _WIN32
#include "GraphicsAPI.h"
#else
#include "Production/NativeGraphics.h"
#endif

#include <array>

namespace orbiter::vulkan {

inline VECTOR3 Add(const VECTOR3& a, const VECTOR3& b)
{
    return {a.x + b.x, a.y + b.y, a.z + b.z};
}

inline VECTOR3 Subtract(const VECTOR3& a, const VECTOR3& b)
{
    return {a.x - b.x, a.y - b.y, a.z - b.z};
}

inline VECTOR3 Scale(const VECTOR3& v, double s)
{
    return {v.x * s, v.y * s, v.z * s};
}

inline double Dot(const VECTOR3& a, const VECTOR3& b)
{
    return a.x * b.x + a.y * b.y + a.z * b.z;
}

inline std::array<VECTOR3, 3> Axes(const MATRIX3& m)
{
    return {{{m.m11, m.m21, m.m31}, {m.m12, m.m22, m.m32}, {m.m13, m.m23, m.m33}}};
}

struct SceneFrame {
    VECTOR3 origin{};
    std::array<VECTOR3, 3> axes{};

    VECTOR3 Rotate(const VECTOR3& v) const
    {
        return Add(Add(Scale(axes[0], v.x), Scale(axes[1], v.y)), Scale(axes[2], v.z));
    }

    VECTOR3 ToGlobal(const VECTOR3& local) const { return Add(origin, Rotate(local)); }

    VECTOR3 ToLocal(const VECTOR3& global) const
    {
        const auto local = Subtract(global, origin);
        return {Dot(axes[0], local), Dot(axes[1], local), Dot(axes[2], local)};
    }
};

inline SceneFrame ObjectFrame(OBJHANDLE object)
{
    MATRIX3 rotation;
    VECTOR3 position;
    oapiGetRotationMatrix(object, &rotation);
    oapiGetGlobalPos(object, &position);
    return {position, Axes(rotation)};
}

inline VECTOR3 SunPosition()
{
    VECTOR3 sun{};
    if (const auto body = oapiGetGbodyByIndex(0)) oapiGetGlobalPos(body, &sun);
    return sun;
}

} // namespace orbiter::vulkan
