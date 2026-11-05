// Licensed under the MIT License.
#pragma once
#include "../Vecmat.h"
#include <cmath>

namespace orbiter::production {
// Recorder endpoints come from finite Euler rotations. Near a half turn the
// original matrix-to-quaternion trace branch can lose unit length, putting its
// dot product outside acos's domain. Preserve the original interpolation for
// every in-domain pair; repair only that invalid recorded-input calculation.
inline void InterpolateRecordedAttitude(Quaternion& result,
    const Quaternion& first, const Quaternion& second, double fraction)
{
    const double product=dotp(first,second);
    const double firstNorm=first.norm2(),secondNorm=second.norm2();
    if (!(std::abs(product)>1.0) || !std::isfinite(product) ||
        !std::isfinite(firstNorm) || !std::isfinite(secondNorm) ||
        firstNorm<=0.0 || secondNorm<=0.0 || !std::isfinite(fraction)) {
        result.interp(first,second,fraction);
        return;
    }
    Quaternion a(first),b(second);
    auto normalize=[](Quaternion& q) {
        const double scale=1.0/std::sqrt(q.norm2());
        q.qvx*=scale;q.qvy*=scale;q.qvz*=scale;q.qs*=scale;
    };
    normalize(a);normalize(b);
    const double unitProduct=dotp(a,b);
    if (std::abs(unitProduct)<1.0) {
        result.interp(a,b,fraction);
        return;
    }
    // A rounded unit dot at either endpoint uses the continuous linear limit.
    const double weight=fraction*(unitProduct<0.0?-1.0:1.0);
    result.Set((1.0-fraction)*a.qvx+weight*b.qvx,
               (1.0-fraction)*a.qvy+weight*b.qvy,
               (1.0-fraction)*a.qvz+weight*b.qvz,
               (1.0-fraction)*a.qs +weight*b.qs);
    normalize(result);
    if (result.qs<0.0) {
        result.qvx=-result.qvx;result.qvy=-result.qvy;
        result.qvz=-result.qvz;result.qs=-result.qs;
    }
}
}
