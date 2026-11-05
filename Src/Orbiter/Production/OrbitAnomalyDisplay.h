// Licensed under the MIT License.
#ifndef ORBITER_PRODUCTION_ORBIT_ANOMALY_DISPLAY_H
#define ORBITER_PRODUCTION_ORBIT_ANOMALY_DISPLAY_H
#include "../Element.h"
#include <cmath>
#include <limits>

namespace orbiter::production {
// A landed body's normalized eccentricity dot product can round one ULP
// outside acos's domain. Recover only this display value from the existing
// cached eccentric anomaly; never modify the Elements object or propagation.
inline double OrbitDisplayTrueAnomaly(const Elements& elements) noexcept {
    const double original=elements.TrueAnm();
    if (std::isfinite(original) || !(elements.e>0.0 && elements.e<1.0) ||
        !std::isfinite(elements.EccAnm())) return original;
    const Vector& position=elements.RVec();
    const Vector& velocity=elements.VVec();
    const double radial=dotp(position,velocity);
    const Vector eccentricity=position*(1.0/elements.Radius()-1.0/elements.a)-
        velocity*(radial/elements.Mu());
    const double argument=dotp(eccentricity,position)/(elements.e*elements.Radius());
    const double magnitude=std::abs(argument);
    if (!(magnitude>1.0 && magnitude<=1.0+2.0*std::numeric_limits<double>::epsilon()))
        return original;
    double recovered=elements.TrueAnomaly_from_EccAnomaly(elements.EccAnm());
    if (!std::isfinite(recovered)) return original;
    if (recovered<0.0 || (recovered==0.0 && radial<0.0)) recovered+=Pi2;
    return recovered==0.0 ? 0.0 : recovered;
}
inline double OrbitDisplayTrueLongitude(const Elements& elements) noexcept {
    const double original=elements.TrueLng();
    if (std::isfinite(original) || std::isfinite(elements.TrueAnm()) ||
        !std::isfinite(elements.omegab)) return original;
    const double anomaly=OrbitDisplayTrueAnomaly(elements);
    if (!std::isfinite(anomaly)) return original;
    double longitude=elements.omegab+anomaly;
    if (longitude>=Pi2) longitude-=Pi2;
    return longitude;
}
}
#endif
