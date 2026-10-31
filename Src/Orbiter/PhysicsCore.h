// Copyright (c) Martin Schweiger
// Licensed under the MIT License
#ifndef ORBITER_PHYSICS_CORE_H
#define ORBITER_PHYSICS_CORE_H
#include "Vecmat.h"
#include "AstroMath.h"

namespace orbiter { namespace physics {
inline Vector PointMassAcceleration(const Vector &rpos, double mass)
{
    double d = rpos.length();
    return rpos * (Ggrav * mass / (d*d*d));
}

inline Vector EulerAcceleration(const Vector &pmi, const Vector &tau, const Vector &omega)
{
    // Original full Euler equation in Orbiter's left-handed system.
    return Vector (
        (tau.x - (pmi.y-pmi.z)*omega.y*omega.z) / pmi.x,
        (tau.y - (pmi.z-pmi.x)*omega.z*omega.x) / pmi.y,
        (tau.z - (pmi.x-pmi.y)*omega.x*omega.y) / pmi.z);
}

inline void FinalizeStage(StateVectors &state, const Vector &rpos_base,
    const Vector &rvel_base, const Vector &rpos_add, const Vector &rvel_add)
{
    state.pos = rpos_base + rpos_add;
    state.vel = rvel_base + rvel_add;
    state.R.Set(state.Q);
}

inline void FlushIncrements(Vector &rpos_base, Vector &rvel_base,
    Vector &rpos_add, Vector &rvel_add, int &updcount)
{
    if (updcount++ == 1000) {
        rpos_base += rpos_add;
        rpos_add.Set(0,0,0);
        rvel_base += rvel_add;
        rvel_add.Set(0,0,0);
        updcount = 0;
    }
}

// Original RK4_LinAng stages and expression ordering. Application force/torque
// evaluation is supplied by callbacks; the numerical body has one implementation.
template<class Moments, class Angular>
void AdvanceRK4(StateVectors &state, const Vector &acc, const Vector &arot,
    Vector &rvel_add, Vector &rpos_add, double h, int nsub, int isub,
    Moments moments, Angular angular)
{
	double h05 = h*0.5;
	double hi6 = h/6.0;

	Vector tau, acc1, aacc1, acc2, aacc2, acc3, aacc3;
	StateVectors sa, sb, sc;
	sa.pos.Set (state.pos+state.vel*h05);
	sa.vel.Set (state.vel+acc*h05);
	sa.SetRot (state.Q.Rot(state.omega*h05));
	sa.omega.Set (state.omega+arot*h05);
	moments (acc1, tau, sa, (isub+0.5)/nsub, h);
	aacc1.Set (angular (tau, sa.omega));

	sb.pos.Set (state.pos+sa.vel*h05);
	sb.vel.Set (state.vel+acc1*h05);
	sb.SetRot (state.Q.Rot(sa.omega*h05));
	sb.omega.Set (state.omega+aacc1*h05);
	moments (acc2, tau, sb, (isub+0.5)/nsub, h);
	aacc2.Set (angular (tau, sb.omega));

	sc.pos.Set (state.pos+sb.vel*h);
	sc.vel.Set (state.vel+acc2*h);
	sc.SetRot (state.Q.Rot(sb.omega*h));
	sc.omega.Set (state.omega+aacc2*h);
	moments (acc3, tau, sc, (isub+1.0)/nsub, h);
	aacc3.Set (angular (tau, sc.omega));

	rvel_add += (acc +(acc1+acc2)*2.0+acc3)*hi6;
	rpos_add += (state.vel+(sa.vel+sb.vel)*2.0+sc.vel)*hi6;
	state.Q.Rotate ((state.omega+(sa.omega+sb.omega)*2.0+sc.omega)*hi6);
	state.omega += (arot+(aacc1+aacc2)*2.0+aacc3)*hi6;
}
}}
#endif
