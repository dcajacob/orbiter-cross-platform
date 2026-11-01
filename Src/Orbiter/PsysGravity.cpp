// Copyright (c) Martin Schweiger
// Licensed under the MIT License
// Original planetary-system force calculations, shared by both applications.
#include "PsysCore.h"
#include "PhysicsCore.h"
#include "OrbiterCelestialData.h"

void PlanetarySystem::ScanGFieldSources (const Vector *gpos, const Body *exclude, GFieldData *gfd) const
{
	const double min_contrib = 1e-6; // min. rel. g-field contribution threshold
	orbiter::production::UInt32 i, j, idx;
	double a, atot = 0.0;
	gfd->ngrav = 0; // reset gravitation source list
	for (i = 0; i < celestials.size(); i++)
		if (celestials[i] != exclude)
			atot += celestials[i]->Mass() / gpos->dist2 (celestials[i]->GPos());
	for (i = 0; i < celestials.size(); i++) {
		if (celestials[i] != exclude) {
			a = celestials[i]->Mass() / gpos->dist2 (celestials[i]->GPos());
			if (a > min_contrib*atot) {
				if (gfd->ngrav < MAXGFIELDLIST)
					gfd->gravidx[gfd->ngrav++] = i;
				else { // find current smallest contribution
					double a2, amin = 1e100;
					orbiter::production::UInt32 jmin = MAXGFIELDLIST;
					// this search is not very efficient, but shouldn't be
					// called very often
					for (j = 0; j < MAXGFIELDLIST; j++) {
						idx = gfd->gravidx[j];
						a2 = celestials[idx]->Mass() / gpos->dist2 (celestials[idx]->GPos());
						if (a2 < amin) amin = a2, jmin = j;
					}
					if (amin < a) gfd->gravidx[jmin] = i; // replace
				}
			}
		}
	}
	gfd->testidx = 0;
}

void PlanetarySystem::UpdateGFieldSources (const Vector *gpos, const Body *exclude, GFieldData *gfd) const
{
	extern const orbiter::production::UInt32 MAXGFIELDLIST;
	const double min_contrib = 1e-6; // min. g-field contribution threshold
	orbiter::production::UInt32 i, idx, imin;
	double a, atot = 0.0, amin = 1e100;
	Vector acc;
	bool testnext = true;

	// First, check we can drop the weakest member of the current list
	for (i = 0; i < gfd->ngrav; i++) {
		idx = gfd->gravidx[i];
		if (celestials[idx] != exclude) {
			Vector acci = SingleGacc (celestials[idx]->GPos() - *gpos, celestials[idx]);
			acc += acci;
			a = acci.length();
			atot += a;
			if (a < amin) amin = a, imin = i;
		}
		if (gfd->testidx == idx) testnext = false;
	}
	if (amin < min_contrib*atot) {
		for (i = imin+1; i < gfd->ngrav; i++)
			gfd->gravidx[i-1] = gfd->gravidx[i];
		gfd->ngrav--;
	}

	// Test next candidate for inclusion in the list
	if (testnext && exclude != celestials[idx = gfd->testidx]) {
		Vector acci = SingleGacc (celestials[idx]->GPos() - *gpos, celestials[idx]);
		a = acci.length();
		if (a > min_contrib*atot) {
			if (gfd->ngrav < MAXGFIELDLIST) gfd->gravidx[gfd->ngrav++] = idx;
			else if (a > amin) gfd->gravidx[imin] = idx;
		}
	}
	if (++gfd->testidx == celestials.size()) gfd->testidx = 0;
}

Vector PlanetarySystem::GaccAt (double t, const Vector &gpos, const Body *exclude) const
{
	Vector r, acc, pos, closepos;
	CelestialBody *closep = 0;
	const CelestialBody *sec;
	orbiter::production::UInt32 i;
	double d, dmin = 1e100;

	// pass 1: sun and primary planets
	for (i = 0; i < celestials.size(); i++) {
		if (exclude == celestials[i]) continue;
		if (celestials[i]->Primary() &&
			celestials[i]->Primary()->Type() == OBJTP_PLANET) continue;
		if (celestials[i]->Type() == OBJTP_PLANET) {
			if (!celestials[i]->PositionAtTime (t, &pos)) continue;
		} else pos.Set(0,0,0); // sun assumed in origin
		r.Set(pos - gpos);
		d = r.length();
		acc += r * (Ggrav * celestials[i]->Mass() / (d*d*d));
		if (d < dmin) dmin = d, closep = celestials[i], closepos.Set(pos);
	}
	// pass 2: moons of closest planet
	if (closep && closep->Type() == OBJTP_PLANET) {
		for (i = 0; i < closep->nSecondary(); i++) {
			sec = closep->Secondary(i);
			if (!sec->PositionAtTime (t, &pos)) continue;
			pos += closepos;
			r.Set(pos - gpos);
			d = r.length();
			acc += r * (Ggrav * sec->Mass() / (d*d*d));
		}
	}
	return acc;
}

Vector SingleGacc_perturbation (const Vector &rpos, const CelestialBody *body)
{
	// Calculate perturbation of gravitational acceleration due to nonspherical
	// shape of the body.
	// rpos: relative position of 'bodies' wrt. r (global frame)

	Vector dg;

	if (body->UseComplexGravity() && body->usePines()) {

		//Rotate position vector into the planet's local frame
		Matrix rot = body->GRot();
		Vector lpos = -tmul(rot,rpos)/1000.0;

		//Convert to right-handed
		double temp_y;
		temp_y = lpos.y;
		lpos.y = lpos.z;
		lpos.z = temp_y;

		unsigned int maxDegreeOrder = body->GetPinesCutoff();
		//get aceleration vector from spherical harmonics
		{
			//Limit scope of the const cast. the internal state of body.PinesGravProp does need to change when this finction is called.
			CelestialBody* unconstbody = const_cast<CelestialBody*>(body);
			dg = unconstbody->pinesAccel(lpos, maxDegreeOrder, maxDegreeOrder);
		}

		//Convert back to Orbiter's lefthandedness
		temp_y = dg.y;
		dg.y = dg.z;
		dg.z = temp_y;

		//rotate back into global frame
		dg = mul(rot, dg) * 1000.0;

		//Useful debug string. Make sure you only have one vessel in your scenerio if you us it...
		//double radial = dg.length() * 100000.0 * dotp(rpos.unit(), dg.unit());
		//sprintf(DBG_MSG, "<%lf %lf %lf> Magnitude: %lf mGal Radial: %lf Radialness: %lf", dg.x * 100000.0, dg.y * 100000.0, dg.z * 100000.0, dg.length()*100000.0, radial,  dotp(rpos.unit(), dg.unit()));
		return dg;
	}
	else if (body->UseComplexGravity() && body->nJcoeff() > 0) {

		const double eps = 1e-10; // perturbation limit
		double d  = rpos.length();
		double Rr = body->Size() / d;
		double Rrn = Rr*Rr;
		double gacc_r = 0.0, gacc_p = 0.0;

		// J2 perturbation term
		double Jn_Rrn = body->Jcoeff(0) * Rrn;  // relative influence of J2 term
		if (fabs (Jn_Rrn) > eps) {
			Vector er (rpos.unit());  // radial unit vector
			Vector loc (tmul (body->GRot(), er));
			double lat = asin(-loc.y), slat = sin(lat), clat = cos(lat); // latitude
			gacc_r += 1.5 * Jn_Rrn * (1.0 - 3.0*slat*slat);
			gacc_p += 3.0 * Jn_Rrn * clat*slat;

			// J3 perturbation term
			if (body->nJcoeff() > 1) {
				Rrn *= Rr;
				Jn_Rrn = body->Jcoeff(1) * Rrn;  // relative influence of J3 term
				if (fabs (Jn_Rrn) > eps) {
					gacc_r += 2.0 * Jn_Rrn * slat * (3.0 - 5.0*slat*slat);
					gacc_p += 1.5 * Jn_Rrn * clat * (-1.0 + 5.0*slat*slat);

					// J4 perturbation term
					if (body->nJcoeff() > 2) {
						Rrn *= Rr;
						Jn_Rrn = body->Jcoeff(2) * Rrn;
						if (fabs (Jn_Rrn) > eps) {
							gacc_r += -0.625 * Jn_Rrn * (3.0 + slat*slat*(-30.0 + 35.0*slat*slat));
							gacc_p += 2.5 * Jn_Rrn * clat*slat * (-3.0 + 7.0*slat*slat);
						}
					}
				}
			}
			double GM = Ggrav * body->Mass();
			double T0 = GM / (d*d);

			Vector ep, ea (crossp (er, body->RotAxis())); // azimuth vector
			double lea = ea.length();
			if (lea > eps) ep.Set (crossp (er, ea/lea));  // polar unit vector
			else ep.Set (0,0,0);
			dg = er * (T0*gacc_r) + ep * (T0*gacc_p);
		}
	}
	return dg;
}

Vector SingleGacc (const Vector &rpos, const CelestialBody *body)
{
	// Calculate gravitational acceleration at a position r from a single source
	// rpos: relative position of 'body' wrt. r (global coords)

	return orbiter::physics::PointMassAcceleration(rpos, body->Mass()) + SingleGacc_perturbation (rpos, body);
}

Vector PlanetarySystem::Gacc (const Vector &gpos, const Body *exclude, const GFieldData *gfd) const
{
	Vector acc;
	orbiter::production::UInt32 i, j;

	if (gfd) {
		for (j = 0; j < gfd->ngrav; j++) {
			i = gfd->gravidx[j];
			if (exclude == celestials[i]) continue;
			acc += SingleGacc (celestials[i]->s0->pos - gpos, celestials[i]);
		}
	} else {
		for (i = 0; i < celestials.size(); i++) {
			if (exclude == celestials[i]) continue;
			acc += SingleGacc (celestials[i]->s0->pos - gpos, celestials[i]);
		}
	}
	return acc;
}

Vector PlanetarySystem::Gacc_intermediate (const Vector &gpos, double n, const Body *exclude, GFieldData *gfd) const
{
	Vector acc;
	orbiter::production::UInt32 i, j;

	if (gfd) { // use body's source list
		for (j = 0; j < gfd->ngrav; j++) {
			i = gfd->gravidx[j];
			if (exclude == celestials[i]) continue;
			acc += SingleGacc (celestials[i]->InterpolatePosition (n) - gpos, celestials[i]);
		}
	} else { // use full gbody list
		for (i = 0; i < celestials.size(); i++) {
			if (exclude == celestials[i]) continue;
			acc += SingleGacc (celestials[i]->InterpolatePosition (n) - gpos, celestials[i]);
		}
	}
	return acc;
}

Vector PlanetarySystem::Gacc_intermediate_pert (const CelestialBody *cbody, const Vector &relpos, double n, const Body *exclude, GFieldData *gfd) const
{
	Vector acc;
	orbiter::production::UInt32 i, j;
	Vector gpos = relpos + cbody->InterpolatePosition (n);

	if (gfd) { // use body's source list
		for (j = 0; j < gfd->ngrav; j++) {
			i = gfd->gravidx[j];
			if (exclude == celestials[i]) continue;
			if (cbody == celestials[i])
				acc += SingleGacc_perturbation (-relpos, celestials[i]);
			else
				acc += SingleGacc (celestials[i]->InterpolatePosition (n) - gpos, celestials[i]);
		}
	} else { // use full gbody list
		for (i = 0; i < celestials.size(); i++) {
			if (exclude == celestials[i]) continue;
			if (cbody == celestials[i])
				acc += SingleGacc_perturbation (-relpos, celestials[i]);
			else
				acc += SingleGacc (celestials[i]->InterpolatePosition (n) - gpos, celestials[i]);
		}
	}
	return acc;
}

Vector PlanetarySystem::GaccRel (const Vector &rpos, const CelestialBody *cbody, double n, const Body *exclude, GFieldData *gfd) const
{
	Vector acc;
	orbiter::production::UInt32 i, j;

	Vector gpos (rpos + cbody->InterpolatePosition (n));

	if (gfd) { // use bodies's source list
		for (j = 0; j < gfd->ngrav; j++) {
			i = gfd->gravidx[j];
			if (exclude == celestials[i]) continue;
			acc += SingleGacc (celestials[i]->InterpolatePosition (n) - gpos, celestials[i]);
		}
	} else { // use full gbody list
		for (i = 0; i < celestials.size(); i++) {
			if (exclude == celestials[i]) continue;
			acc += SingleGacc (celestials[i]->InterpolatePosition (n) - gpos, celestials[i]);
		}
	}
	return acc;
}

Vector PlanetarySystem::GaccPn_perturbation (const Vector &gpos, double n, const CelestialBody *cbody) const
{
	return SingleGacc_perturbation (cbody->InterpolatePosition (n) - gpos, cbody);
}

CelestialBody *PlanetarySystem::GetDominantGravitySource (const Vector &gpos, double &gfrac)
{
	// assumes spherical gravity sources
	orbiter::production::UInt32 i;
	double g, gtot = 0.0, gmax = 0.0;
	CelestialBody *body = 0;

	for (i = 0; i < celestials.size(); i++) {
		Vector r(celestials[i]->GPos() - gpos);
		gtot += (g = celestials[i]->Mass() / r.length2());
		if (g > gmax) {
			gmax = g;
			body = celestials[i];
		}
	}
	gfrac = (body ? gmax/gtot : 0.0);
	return body;
}

double PlanetarySystem::GetGravityContribution (const Body *body, const Vector &gpos, bool *dominant)
{
	// assumes spherical gravity sources
	orbiter::production::UInt32 i;
	double g, gtot = 0.0, gbody = 0.0, gmax = 0.0;

	for (i = 0; i < celestials.size(); i++) {
		Vector r(celestials[i]->GPos() - gpos);
		gtot += (g = celestials[i]->Mass() / r.length2());
		if (celestials[i] == body) gbody = g;
		if (g > gmax) gmax = g;
	}
	if (dominant) *dominant = (gmax == gbody);
	return (gtot ? gbody/gtot : 0.0);
}

Vector PlanetarySystem::GetMomentumFlux (const Vector &gpos) const
{
	const double L = 3.846e26;      // sun luminosity [W] - SHOULD BE CONFIGURABLE!
	const double F = L/(4.0*PI*C0); // radiation force at unit distance
	double r2 = gpos.length2();
	double p  = F/r2;               // radiation pressure at distance r
	return gpos * (p/sqrt(r2));
}
