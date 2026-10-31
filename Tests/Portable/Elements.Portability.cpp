// Licensed under the MIT License. Exercises original orbital calculations.
#include "Element.h"
#include "TimeData.h"
#include <cmath>
#include <iostream>
#include <stdexcept>

namespace {
constexpr double epoch = 51544.5;
constexpr double mass = 5.972e24;
void require(bool value, const char *message) {
    if (!value) throw std::runtime_error(message);
}
void close(double value, double expected, double tolerance, const char *message) {
    require(std::isfinite(value) && std::abs(value-expected) <= tolerance, message);
}
void close(const Vector &a, const Vector &b, double tolerance, const char *message) {
    close((a-b).length(), 0, tolerance, message);
}
void conic(double a, double eccentricity, double inclination) {
    Elements elements(a, eccentricity, inclination, .5, .8, .1, epoch, epoch);
    elements.Setup(1000, mass, epoch, epoch);
    for (double time : {-600.0, 0.0, 1000.0, 3600.0}) {
        Vector r, v, updatedR, updatedV;
        elements.PosVel(r, v, time);
        elements.Update(updatedR, updatedV, time);
        close(r, updatedR, 1e-4, "explicit Update position differs from PosVel");
        close(v, updatedV, 1e-7, "explicit Update velocity differs from PosVel");
        const double mu = elements.Mu();
        const double energy = .5*v.length2() - mu/r.length();
        close(energy/(-mu/(2*a)), 1, 1e-12, "conic specific energy");
        close(crossp(r,v).length2()/(mu*a*(1-eccentricity*eccentricity)),
              1, 1e-12, "conic angular momentum");
        Elements recovered(epoch);
        recovered.Setup(1000, mass, epoch, epoch);
        recovered.Calculate(r, v, time);
        Vector roundR, roundV;
        recovered.PosVel(roundR, roundV, time);
        close(roundR, r, .001, "state/elements position round trip");
        close(roundV, v, 1e-6, "state/elements velocity round trip");
        Elements copied(elements, epoch);
        copied.PosVel(roundR, roundV, time);
        close(roundR, r, 1e-6, "explicit-context copy position");
        close(roundV, v, 1e-8, "explicit-context copy velocity");
    }
}
}

int main() {
    try {
        conic(7000000, 0, 0);         // circular, equatorial
        conic(10000000, .2, 0);       // eccentric, equatorial
        conic(10000000, .7, .8);      // eccentric, inclined
        conic(-10000000, 1.5, .4);    // hyperbolic, inbound and outbound
        Elements circle(7000000, 0, 0, 0, 0, 0, epoch, epoch);
        circle.Setup(1000, mass, epoch, epoch);
        Vector r, v;
        circle.PosVel(r, v, circle.OrbitT()/4);
        close(r, Vector(0,0,7000000), 1e-6, "circular quarter-orbit position");
        close(v, Vector(-std::sqrt(circle.Mu()/7000000),0,0), 1e-8,
              "circular quarter-orbit velocity");

        Elements shifted(10000000,.2,.3,.5,.8,.1,epoch,epoch+10);
        Elements original(10000000,.2,.3,.5,.8,.1,epoch,epoch);
        shifted.Setup(1000,mass,epoch,epoch+10);
        original.Setup(1000,mass,epoch,epoch);
        Vector otherR, otherV;
        original.PosVel(r,v,1000);
        shifted.PosVel(otherR,otherV,1000-10*86400);
        close(r,otherR,.005,"independent reference-epoch position");
        close(v,otherV,1e-5,"independent reference-epoch velocity");
        shifted.Set(original,epoch);
        shifted.PosVel(otherR,otherV,1000);
        close(r,otherR,1e-6,"explicit-context Set");
        shifted.Reset(7000000,0,0,0,0,0,epoch,epoch);
        shifted.PosVel(r,v,0);
        close(r,Vector(7000000,0,0),1e-6,"explicit-context Reset");

        TimeData time;
        time.Reset(epoch);
        time.SetFixedStep(1);
        time.BeginStep(.01,true);
        close(time.SimT1,1,0,"fixed simulation step independent of wall clock");
        time.EndStep(true);
        time.BeginStep(.3,false);
        time.EndStep(false);
        close(time.SimT0,1,0,"pause preserves simulation time");
        time.JumpTo(epoch+.5);
        close(time.SimT0,43200,0,"explicit MJD jump");
        std::cout << "PASS: circular/eccentric/inclined/hyperbolic elements, round trips, explicit epochs and stepping\n";
        return 0;
    } catch (const std::exception &error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
