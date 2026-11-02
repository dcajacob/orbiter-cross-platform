// Licensed under the MIT License
#include "Production/RigidBodyServices.h"
#include "Production/Random.h"
#include "PhysicsTrace.h"
#include <cmath>
#include <cstdlib>
#include <iostream>
#include <stdexcept>
using namespace orbiter::production;
void require(bool value, const char* message) { if (!value) throw std::runtime_error(message); }

// An explicit empty force field for an independent inertial/free-spin test.
// Reference/perturbation queries fail; this is not a substitute planetary system.
struct Environment final : BodyServices, RigidBodyServices {
    CFG_PHYSICSPRM physics{};
    TimeData time;
    bool updating = false;
    bool IsUpdating() const override { return updating; }
    std::filesystem::path ConfigPath(const char*) override { throw std::logic_error("No configuration in inertial test"); }
    void LoadStatus(const char*, int) override { throw std::logic_error("No file loading in inertial test"); }
    void SizeChanged(Body*) override { throw std::logic_error("Unexpected size notification"); }
    void VisualEvent(Body*, BodyVisual, BodyParameter, BodyContent) override { throw std::logic_error("No renderer in inertial test"); }
    void CheckUpdateState(bool valid) override { require(valid, "Unavailable body update state"); }
    TimeData& Time() override { return time; }
    const CFG_PHYSICSPRM& Physics() const override { return physics; }
    PlanetarySystem* World() const override { return nullptr; }
    const Body& Reference(const CelestialBody*) const override { throw std::logic_error("No primary in inertial test"); }
    Vector ReferencePosition(const CelestialBody*, double) const override { throw std::logic_error("No ephemeris in inertial test"); }
    double GravityContribution(const CelestialBody*, const Vector&) const override { throw std::logic_error("No primary in inertial test"); }
    void ScanGravity(const PlanetarySystem* world, const Vector&, const Body*, GFieldData* data, bool) const override
    { require(!world, "Unexpected world identity"); data->ngrav = 0; }
    Vector Acceleration(const Vector&, double, const Body*, GFieldData*) const override { return Vector(0,0,0); }
    Vector PerturbedAcceleration(const CelestialBody*, const Vector&, double, const Body*, GFieldData*) const override
    { throw std::logic_error("No perturbation field in inertial test"); }
    Vector RelativeAcceleration(const Vector&, const CelestialBody*, double, const CelestialBody*, GFieldData*) const override
    { throw std::logic_error("No relative field in inertial test"); }
    Vector NonsphericalAcceleration(const Vector&, const CelestialBody*) const override
    { throw std::logic_error("No nonspherical field in inertial test"); }
    void TraceAllocation(const char*, int) override {} // no diagnostic logger requested by this test
};
struct InertialBody final : RigidBody {
    explicit InertialBody(const Vector& omega) : RigidBody(1,1,Vector(1,1,1))
    {
        SetDefaultState();
        RPlace(Vector(7000000,0,0), Vector(0,10,0));
        s0->Q.Set(0,0,0,1); s0->R = IMatrix(); s0->omega = omega;
        cpos = s0->pos; cvel = s0->vel; acc.Set(0,0,0);
    }
};
struct Result { Vector position, velocity, omega; Quaternion rotation; };
Result run(Environment& env, int propagator, const std::filesystem::path& output)
{
    std::srand(0);SeedRandom(0); // same recorded seed, including flush scheduling
    env.physics.nLPropLevel = 1;
    env.physics.PropMode[0] = propagator;
    env.physics.PropTTgt[0] = env.physics.PropATgt[0] = 1e10;
    env.physics.PropSubMax = 1;
    env.time.Reset(51544.5); env.time.SetFixedStep(.25);
    RigidBody::GlobalSetup();
    const Vector omega(1e-5,2e-5,-3e-5);
    InertialBody body(omega);
    orbiter::PhysicsTrace trace;
    trace.Open(output.string());
    auto sample = [&](std::size_t step) {
        const auto& p=body.GPos(); const auto& v=body.GVel(); const auto& q=body.GQ(); const auto& w=body.AngularVelocity();
        trace.Write({step,env.time.SimT0,env.time.MJD0,{p.x,p.y,p.z},{v.x,v.y,v.z},
            {q.qvx,q.qvy,q.qvz,q.qs},{w.x,w.y,w.z}});
    };
    sample(0);
    const double initialEnergy = dotp(omega,omega)*.5;
    for (int tick = 0; tick < 6000; ++tick) {
        env.time.BeginStep(.01,true); env.updating = true;
        body.BeginStateUpdate(); body.Update(false); env.updating = false;
        body.EndStateUpdate(); env.time.EndStep(true);
        if ((tick+1)%10==0) sample(tick+1);
        require(std::abs(dotp(body.AngularVelocity(),body.AngularVelocity())*.5/initialEnergy-1) <= 1e-8,
            "Free-spin energy drift exceeds budget");
        require((mul(body.GRot(),body.AngularMomentum())-omega).length()/omega.length() <= 1e-8,
            "Free-spin global angular momentum drift exceeds budget");
    }
    const double seconds = 6000*.25;
    require((body.GPos()-Vector(7000000,10*seconds,0)).length() <= .01, "Inertial position budget exceeded");
    require((body.GVel()-Vector(0,10,0)).length() <= 1e-5, "Inertial velocity budget exceeded");
    require((body.AngularVelocity()-omega).length() <= 1e-10, "Free-spin angular velocity budget exceeded");
    const double angle = omega.length()*seconds;
    const double scale = std::sin(angle/2)/omega.length();
    const Quaternion expected(omega.x*scale,omega.y*scale,omega.z*scale,std::cos(angle/2));
    const auto& q = body.GQ();
    const double sign = q.qs*expected.qs + q.qvx*expected.qvx + q.qvy*expected.qvy + q.qvz*expected.qvz >= 0 ? 1 : -1;
    const double difference = std::sqrt(std::pow(q.qs-sign*expected.qs,2)+std::pow(q.qvx-sign*expected.qvx,2)+
        std::pow(q.qvy-sign*expected.qvy,2)+std::pow(q.qvz-sign*expected.qvz,2));
    require(4*std::asin(difference/2) <= 1e-8, "Analytical free-spin rotation budget exceeded");
    trace.Close();
    return {body.GPos(),body.GVel(),body.AngularVelocity(),q};
}
int main(int argc, char** argv)
{
    try {
        Environment env;
        require(argc==2, "Expected trace output directory");
        const std::filesystem::path output(argv[1]);
        std::filesystem::create_directories(output);
        auto* oldBody = BindBodyServices(&env);
        auto* oldRigid = BindRigidBodyServices(&env);
        for (int mode = 0; mode < NPROP_METHOD; ++mode) {
            const auto path=output/("production-rigid-"+std::to_string(mode)+".csv");
            const auto repeat=output/("production-rigid-"+std::to_string(mode)+"-repeat.csv");
            const auto a=run(env,mode,path),b=run(env,mode,repeat);
            auto bytes=[](const std::filesystem::path& name) {
                std::ifstream file(name,std::ios::binary);
                return std::string(std::istreambuf_iterator<char>(file),std::istreambuf_iterator<char>());
            };
            require(bytes(path)==bytes(repeat), "Production propagator numerical traces differ");
            auto same = [](const Vector& x, const Vector& y) { return x.x==y.x && x.y==y.y && x.z==y.z; };
            require(same(a.position,b.position) && same(a.velocity,b.velocity) && same(a.omega,b.omega) &&
                a.rotation.qs==b.rotation.qs && a.rotation.qvx==b.rotation.qvx && a.rotation.qvy==b.rotation.qvy && a.rotation.qvz==b.rotation.qvz,
                "Production propagator did not repeat exactly");
            std::cout << RigidBody::PropagatorStr(mode) << ": 6000 inertial/free-spin steps, analytical budgets and repeat passed\n";
        }
        BindRigidBodyServices(oldRigid); BindBodyServices(oldBody);
        return 0;
    } catch (const std::exception& error) { std::cerr << error.what() << '\n'; return 1; }
}
