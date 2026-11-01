// Copyright (c) Martin Schweiger
// Licensed under the MIT License

#include "elevmgr.h"
#include "Celbody.h"
#include <algorithm>
#include <climits>
#include <cstdio>
#include <stdexcept>
#include <cstring>
#include <cmath>
#include <filesystem>

using std::min;
using std::max;

static int elev_grid = 256;
static int elev_stride = elev_grid+3;



ElevationManager::ElevationManager(const CelestialBody* body)
: ElevationManager(body,orbiter::production::GetElevationServices().Setup(*body),orbiter::production::GetElevationServices()) {}

ElevationManager::ElevationManager(const CelestialBody* body,const orbiter::production::ElevationSetup& setup,
    orbiter::production::ElevationServices& host)
: services(&host), cbody(body)
{
    if (!body || setup.mode<0 || setup.mode>2 || setup.maximumLevel<0 || setup.maximumLevel>14 ||
        !std::isfinite(setup.resolution) || setup.resolution<=0 || setup.tileSources<1 || setup.tileSources>3)
        throw std::invalid_argument("Invalid production elevation configuration");
    mode=setup.mode;tilesource=setup.tileSources;maxlvl=setup.maximumLevel;elev_res=setup.resolution;
    std::unique_ptr<ZTreeMgr> primary,modified;
    if (tilesource & 0x0002) {
        primary=services->OpenArchive(*cbody,false);
        modified=services->OpenArchive(*cbody,true);
    }
    bDirExists=services->HasLooseLayer(*cbody,false);
    bModExists=services->HasLooseLayer(*cbody,true);
    for (auto& tree:treeMgr) tree=nullptr;
    treeMgr[0]=primary.release();treeMgr[1]=modified.release();
}

ElevationManager::~ElevationManager ()
{
	if (local_cache) delete local_cache;
	for (int i = 0; i < 2; i++)
		if (treeMgr[i])
			delete treeMgr[i];
}


int ElevationManager::Quadrant(double lat, double lng, int lvl) const
{
	// 0 = North-West, 1 = North-East, 2 = South-West, 3 = South-East corner
	int nlat = 1 << (lvl + 1);
	int nlng = 2 << (lvl + 1);
	int ilat = (int)((Pi05 - lat) / Pi * nlat);
	int ilng = (int)((lng + Pi) / Pi2 * nlng);
	int q = 0;
	if (ilng & 1) q += 1;
	if (ilat & 1) q += 2;
	return q;
}

bool ElevationManager::TileIdx (double lat, double lng, int lvl, int *ilat, int *ilng) const
{
	int nlat = 1 << lvl;
	int nlng = 2 << lvl;

	*ilat = (int)((Pi05-lat)/Pi * nlat);
	*ilng = (int)((lng+Pi)/Pi2 * nlng);
	return true;
}

// Tile quadrants and mask bits
// +--------+--------+
// |        |        |
// |   NW   |   NE   |
// |  bit 0 |  bit 1 |
// +--------+--------+
// |        |        |
// |   SW   |   SE   |
// |  bit 2 |  bit 3 |
// +--------+--------+
// tile index (ilat=0 and ilng=0) lies in a NW corner
// lat(PI) = North pole, lat(-PI) = South Pole
// lng(-PI) = 180deg West, lng(PI) = 180deg East

double ElevationManager::Elevation (double lat, double lng, int reqlvl, std::vector<ElevationTile> *tilecache, Vector *normal, int *reslvl) const
{
	double e = 0.0;
	if (reslvl) *reslvl = 0;
	reqlvl = (reqlvl ? min (max(0,reqlvl-7), maxlvl) : maxlvl);

	if (mode) {
		ElevationTile *tile;
		int ntile = 0;
		if (tilecache) {
			tile = tilecache->data();
			ntile = tilecache->size();
		}

		if (!ntile) {
			if (!local_cache) local_cache = new std::vector<ElevationTile>(8);
			tile = local_cache->data();
			ntile = local_cache->size();
		}

		int i, lvl, ilat, ilng;
		ElevationTile *t = 0;

		for (i = 0; i < ntile; i++) {
			if (tile[i].data &&
				reqlvl == tile[i].tgtlvl && tile[i].mgr == this &&
				lat >= tile[i].latmin && lat <= tile[i].latmax &&
				lng >= tile[i].lngmin && lng <= tile[i].lngmax) {
				int q = -1;
				if (tile[i].quadrants != 0) { // Tile contain higher lvl data for some of it's quadtants
					q = 0;
					// Calculate quadrant being accessed
					if (lng > (tile[i].lngmin + tile[i].lngmax) * 0.5) q += 1;
					if (lat < (tile[i].latmin + tile[i].latmax) * 0.5) q += 2;
					if (tile[i].quadrants & (1 << q)) continue; // Tile not usable, continue search
				}
				//oapiWriteLogV("CacheHit idx=%d, lvl=%d, f=0x%X, q=%d, ilat=%d, ilng=%d", i, tile[i].lvl, tile[i].quadrants, q, tile[i].ilat, tile[i].ilng);
				t = tile + i;
				break;
			}
		}
		if (!t) { // correct tile not in list - need to load from file
			t = tile;  // find oldest tile
			for (i = 1; i < ntile; i++) 
				if (tile[i].last_access < t->last_access)
					t = tile+i;

			if (t->data) t->Clear();

			for (lvl = reqlvl; lvl >= 0; lvl--) {
				TileIdx (lat, lng, lvl, &ilat, &ilng);
				t->data = LoadElevationTile (lvl+4, ilat, ilng, elev_res);
				if (t->data) {
					LoadElevationTile_mod (lvl+4, ilat, ilng, elev_res, t->data); // load modifications
					int nlat = 1 << lvl;
					int nlng = 2 << lvl;
					t->mgr = this;
					t->lvl = lvl;
					t->ilat = ilat;
					t->ilng = ilng;
					t->tgtlvl = reqlvl;
					t->latmin = (0.5-(double)(ilat+1)/double(nlat))*Pi;
					t->latmax = (0.5-(double)ilat/double(nlat))*Pi;
					t->lngmin = (double)ilng/(double)nlng*Pi2 - Pi;
					t->lngmax = (double)(ilng+1)/(double)nlng*Pi2 - Pi;
					t->quadrants = 0;

					if (reqlvl > lvl) 
					{
						// Check if higher lvl data exists for any of the quadrants, 
						// set flag bit to mark it dirty (un-usable)
						int qlat = ilat * 2, qlng = ilng * 2, qlvl = lvl + 1;
						t->quadrants |= orbiter::production::UInt32(HasElevationTile(qlvl + 4, qlat + 0, qlng + 0)) << 0; // NW
						t->quadrants |= orbiter::production::UInt32(HasElevationTile(qlvl + 4, qlat + 0, qlng + 1)) << 1;	// NE
						t->quadrants |= orbiter::production::UInt32(HasElevationTile(qlvl + 4, qlat + 1, qlng + 0)) << 2; // SW
						t->quadrants |= orbiter::production::UInt32(HasElevationTile(qlvl + 4, qlat + 1, qlng + 1)) << 3;	// SE
					}

					//int q = Quadrant(lat, lng, lvl);
					//oapiWriteLogV("LoadTile[0x%X]: lvl=%d, flags=0x%X, q=%d, i(%d, %d)", t, lvl, t->quadrants, q, ilng, ilat);

					// still need to store emin and emax
					services->Filter(*cbody,ilat,ilng,lvl,elev_res,t->data);
					break;
				}
			}
			t->lat0 = t->lng0 = t->nmlidx = -1;
		}

		if (t->data) {
			std::int16_t *elev_base = t->data+elev_stride+1; // strip padding
			double latidx = (lat-t->latmin) * elev_grid/(t->latmax-t->latmin);
			double lngidx = (lng-t->lngmin) * elev_grid/(t->lngmax-t->lngmin);
			int lat0 = (int)latidx;
			int lng0 = (int)lngidx;
			std::int16_t *eptr = elev_base + lat0*elev_stride + lng0;
			if (mode == 1) { // linear interpolation
				bool tri;
				double w_lat = latidx-lat0;
				double w_lng = lngidx-lng0;

				double e01 = eptr[0]*(1.0-w_lng) + eptr[1]*w_lng;
				double e02 = eptr[elev_stride]*(1.0-w_lng) + eptr[elev_stride+1]*w_lng;
				e = e01*(1.0-w_lat) + e02*w_lat;

				if (normal) {
					double dlat = (t->latmax-t->latmin)/elev_grid;
					double dlng = (t->lngmax-t->lngmin)/elev_grid;
					double dz = dlat * cbody->Size();
					double dx = dlng * cbody->Size() * cos(lat);
					double nx01 = eptr[1]-eptr[0];
					double nx02 = eptr[elev_stride+1]-eptr[elev_stride];
					double nx = w_lat*nx02 + (1.0-w_lat)*nx01;
					Vector vnx(dx,nx,0);
					double nz01 = eptr[elev_stride]-eptr[0];
					double nz02 = eptr[elev_stride+1]-eptr[1];
					double nz = w_lng*nz02 + (1.0-w_lng)*nz01;
					Vector vnz(0,nz,dz);
					*normal = crossp(vnz,vnx).unit();
				}
			} else { // cubic spline interpolation
				// Use the same boundary stencil as the production grid sampler.
				// A tile includes one padding sample, not two past its last edge.
				int latstencil[4] = {-elev_stride,0,elev_stride,2*elev_stride};
				int lngstencil[4] = {-1,0,1,2};
				if (lat0 < 0) latstencil[0] = 0;
				else if (lat0 >= elev_grid) latstencil[3] = elev_stride;
				if (lng0 < 0) lngstencil[0] = 0;
				else if (lng0 >= elev_grid) lngstencil[3] = 1;
				double a_m1, a_0, a_p1, a_p2, b_m1, b_0, b_p1, b_p2;
				double tlat = latidx-lat0;
				double tlng = lngidx-lng0;
				a_m1 = eptr[latstencil[0]+lngstencil[0]];
				a_0  = eptr[latstencil[0]+lngstencil[1]];
				a_p1 = eptr[latstencil[0]+lngstencil[2]];
				a_p2 = eptr[latstencil[0]+lngstencil[3]];
				b_m1 = 0.5 * (2.0*a_0 + tlng*(-a_m1+a_p1) +
					tlng*tlng*(2.0*a_m1-5.0*a_0+4.0*a_p1-a_p2) +
					tlng*tlng*tlng*(-a_m1+3.0*a_0-3.0*a_p1+a_p2));
				a_m1 = eptr[latstencil[1]+lngstencil[0]];
				a_0  = eptr[latstencil[1]+lngstencil[1]];
				a_p1 = eptr[latstencil[1]+lngstencil[2]];
				a_p2 = eptr[latstencil[1]+lngstencil[3]];
				b_0 = 0.5 * (2.0*a_0 + tlng*(-a_m1+a_p1) +
					tlng*tlng*(2.0*a_m1-5.0*a_0+4.0*a_p1-a_p2) +
					tlng*tlng*tlng*(-a_m1+3.0*a_0-3.0*a_p1+a_p2));
				a_m1 = eptr[latstencil[2]+lngstencil[0]];
				a_0  = eptr[latstencil[2]+lngstencil[1]];
				a_p1 = eptr[latstencil[2]+lngstencil[2]];
				a_p2 = eptr[latstencil[2]+lngstencil[3]];
				b_p1 = 0.5 * (2.0*a_0 + tlng*(-a_m1+a_p1) +
					tlng*tlng*(2.0*a_m1-5.0*a_0+4.0*a_p1-a_p2) +
					tlng*tlng*tlng*(-a_m1+3.0*a_0-3.0*a_p1+a_p2));
				a_m1 = eptr[latstencil[3]+lngstencil[0]];
				a_0  = eptr[latstencil[3]+lngstencil[1]];
				a_p1 = eptr[latstencil[3]+lngstencil[2]];
				a_p2 = eptr[latstencil[3]+lngstencil[3]];
				b_p2 = 0.5 * (2.0*a_0 + tlng*(-a_m1+a_p1) +
					tlng*tlng*(2.0*a_m1-5.0*a_0+4.0*a_p1-a_p2) +
					tlng*tlng*tlng*(-a_m1+3.0*a_0-3.0*a_p1+a_p2));
				e =	0.5 * (2.0*b_0 + tlat*(-b_m1+b_p1) +
					tlat*tlat*(2.0*b_m1-5.0*b_0+4.0*b_p1-b_p2) +
					tlat*tlat*tlat*(-b_m1+3.0*b_0-3.0*b_p1+b_p2));
				if (normal) {
					double dlat = (t->latmax-t->latmin)/elev_grid;
					double dlng = (t->lngmax-t->lngmin)/elev_grid;
					double dz = dlat * cbody->Size();
					double dx = dlng * cbody->Size() * cos(lat);
					double dex00 = 0.5*(eptr[lngstencil[2]]-eptr[lngstencil[0]]);
					double dex01 = 0.5*(eptr[lngstencil[3]]-eptr[0]);
					double dex10 = 0.5*(eptr[latstencil[2]+lngstencil[2]]-eptr[latstencil[2]+lngstencil[0]]);
					double dex11 = 0.5*(eptr[latstencil[2]+lngstencil[3]]-eptr[latstencil[2]]);
					double dez00 = 0.5*(eptr[latstencil[2]]-eptr[latstencil[0]]);
					double dez01 = 0.5*(eptr[latstencil[3]]-eptr[0]);
					double dez10 = 0.5*(eptr[latstencil[2]+lngstencil[2]]-eptr[latstencil[0]+lngstencil[2]]);
					double dez11 = 0.5*(eptr[latstencil[3]+lngstencil[2]]-eptr[lngstencil[2]]);
					double w1_lat = latidx - lat0;
					double w0_lat = 1.0-w1_lat;
					double w1_lng = lngidx - lng0;
					double w0_lng = 1.0-w1_lng;
					double dex = (dex00+dex10)*0.5*w0_lng + (dex01+dex11)*0.5*w1_lng;
					double dez = (dez00+dez10)*0.5*w0_lat + (dez01+dez11)*0.5*w1_lat;
					normal->x = -dex;
					normal->z = -dez;
					normal->y = 0.5*(dx+dz);
					normal->unify();
				}
			}
			t->last_access = services->SystemTime();
			t->lat0 = lat0;
			t->lng0 = lng0;
			if (reslvl) *reslvl = t->lvl+7;
		}
	}
	return e*elev_res;
}

void ElevationManager::ElevationGrid (int ilat, int ilng, int lvl, int pilat, int pilng, int plvl, std::int16_t *pelev, float *elev, double *emean) const
{
	int i, j, nmean;
	int nlng = 2 << lvl;
	int nlat = 1 << lvl;
	double lng, lat, e;
	double latmin = Pi05 * (double)(nlat-2*ilat-2)/(double)nlat;
	double latmax = Pi05 * (double)(nlat-2*ilat)/(double)nlat;
	double lngmin = Pi * (double)(2*ilng-nlng)/(double)nlng;
	double lngmax = Pi * (double)(2*ilng-nlng+2)/(double)nlng;
	double dlat = (latmax-latmin)/elev_grid;
	double dlng = (lngmax-lngmin)/elev_grid;

	int pnlng = 2 << plvl;
	int pnlat = 1 << plvl;
	double platmin = Pi05 * (double)(pnlat-2*pilat-2)/(double)pnlat;
	double platmax = Pi05 * (double)(pnlat-2*pilat)/(double)pnlat;
	double plngmin = Pi * (double)(2*pilng-pnlng)/(double)pnlng;
	double plngmax = Pi * (double)(2*pilng-pnlng+2)/(double)pnlng;
	int plat0 = -1000, plng0 = -1000;
	bool pcelldiag = false;

	float *elev_base = elev + elev_stride+1;
	std::int16_t *pelev_base = pelev + elev_stride+1;
	if (emean) {
		*emean = 0.0;
		nmean = 0;
	}
	for (i = -1; i <= elev_grid+1; i++) {
		lat = latmin + i*dlat;
		double latidx = (lat-platmin) * elev_grid/(platmax-platmin);
		int lat0 = (int)floor(latidx);
		for (j = -1; j <= elev_grid+1; j++) {
			lng = lngmin + j*dlng;
			double lngidx = (lng-plngmin) * elev_grid/(plngmax-plngmin);
			int lng0 = (int)floor(lngidx);

			std::int16_t *eptr = pelev_base + lat0*elev_stride + lng0;
			if (mode == 1) { // linear interpolation

				double w_lat = latidx-lat0;
				double w_lng = lngidx-lng0;
				e = (1.0-w_lat)*(eptr[0]*(1.0-w_lng) + eptr[1]*w_lng) + w_lat*(eptr[elev_stride]*(1.0-w_lng) + eptr[elev_stride+1]*w_lng);

			} else { // cubic spline interpolation

				// take care of boundaries
				int latstencil[4] = {-elev_stride,0,elev_stride,2*elev_stride};
				int lngstencil[4] = {-1,0,1,2};
				if (lat0 < 0) latstencil[0] = 0;
				else if (lat0 >= elev_grid) latstencil[3] = elev_stride;
				if (lng0 < 0) lngstencil[0] = 0;
				else if (lng0 >= elev_grid) lngstencil[3] = 1;

				double a_m1, a_0, a_p1, a_p2, b_m1, b_0, b_p1, b_p2;
				double tlat = latidx-lat0;
				double tlng = lngidx-lng0;
				a_m1 = eptr[latstencil[0]+lngstencil[0]];
				a_0  = eptr[latstencil[0]+lngstencil[1]];
				a_p1 = eptr[latstencil[0]+lngstencil[2]];
				a_p2 = eptr[latstencil[0]+lngstencil[3]];
				b_m1 = 0.5 * (2.0*a_0 + tlng*(-a_m1+a_p1) +
					tlng*tlng*(2.0*a_m1-5.0*a_0+4.0*a_p1-a_p2) +
					tlng*tlng*tlng*(-a_m1+3.0*a_0-3.0*a_p1+a_p2));
				a_m1 = eptr[latstencil[1]+lngstencil[0]];
				a_0  = eptr[latstencil[1]+lngstencil[1]];
				a_p1 = eptr[latstencil[1]+lngstencil[2]];
				a_p2 = eptr[latstencil[1]+lngstencil[3]];
				b_0 = 0.5 * (2.0*a_0 + tlng*(-a_m1+a_p1) +
					tlng*tlng*(2.0*a_m1-5.0*a_0+4.0*a_p1-a_p2) +
					tlng*tlng*tlng*(-a_m1+3.0*a_0-3.0*a_p1+a_p2));
				a_m1 = eptr[latstencil[2]+lngstencil[0]];
				a_0  = eptr[latstencil[2]+lngstencil[1]];
				a_p1 = eptr[latstencil[2]+lngstencil[2]];
				a_p2 = eptr[latstencil[2]+lngstencil[3]];
				b_p1 = 0.5 * (2.0*a_0 + tlng*(-a_m1+a_p1) +
					tlng*tlng*(2.0*a_m1-5.0*a_0+4.0*a_p1-a_p2) +
					tlng*tlng*tlng*(-a_m1+3.0*a_0-3.0*a_p1+a_p2));
				a_m1 = eptr[latstencil[3]+lngstencil[0]];
				a_0  = eptr[latstencil[3]+lngstencil[1]];
				a_p1 = eptr[latstencil[3]+lngstencil[2]];
				a_p2 = eptr[latstencil[3]+lngstencil[3]];
				b_p2 = 0.5 * (2.0*a_0 + tlng*(-a_m1+a_p1) +
					tlng*tlng*(2.0*a_m1-5.0*a_0+4.0*a_p1-a_p2) +
					tlng*tlng*tlng*(-a_m1+3.0*a_0-3.0*a_p1+a_p2));
				e =	0.5 * (2.0*b_0 + tlat*(-b_m1+b_p1) +
					tlat*tlat*(2.0*b_m1-5.0*b_0+4.0*b_p1-b_p2) +
					tlat*tlat*tlat*(-b_m1+3.0*b_0-3.0*b_p1+b_p2));
				e = max(-32767.0, min (32766.0, e));
			}
			plat0 = lat0;
			plng0 = lng0;
			elev_base[i*elev_stride+j] = (float)e;
			if (emean && i >= 0 && j >= 0 && i <= elev_grid && j <= elev_grid) {
				*emean += e;
				nmean++;
			}
		}
	}
	if (emean && nmean)
		*emean /= nmean;
}



void ElevationManager::ElevationGrid(int ilat, int ilng, int lvl, int pilat, int pilng, int plvl, std::int16_t* pelev, std::int16_t* elev, double* emean) const
{
	int i, j, nmean;
	int nlng = 2 << lvl;
	int nlat = 1 << lvl;
	double lng, lat, e;
	double latmin = Pi05 * (double)(nlat - 2 * ilat - 2) / (double)nlat;
	double latmax = Pi05 * (double)(nlat - 2 * ilat) / (double)nlat;
	double lngmin = Pi * (double)(2 * ilng - nlng) / (double)nlng;
	double lngmax = Pi * (double)(2 * ilng - nlng + 2) / (double)nlng;
	double dlat = (latmax - latmin) / elev_grid;
	double dlng = (lngmax - lngmin) / elev_grid;

	int pnlng = 2 << plvl;
	int pnlat = 1 << plvl;
	double platmin = Pi05 * (double)(pnlat - 2 * pilat - 2) / (double)pnlat;
	double platmax = Pi05 * (double)(pnlat - 2 * pilat) / (double)pnlat;
	double plngmin = Pi * (double)(2 * pilng - pnlng) / (double)pnlng;
	double plngmax = Pi * (double)(2 * pilng - pnlng + 2) / (double)pnlng;
	int plat0 = -1000, plng0 = -1000;
	bool pcelldiag = false;

	std::int16_t* elev_base = elev + elev_stride + 1;
	std::int16_t* pelev_base = pelev + elev_stride + 1;
	if (emean) {
		*emean = 0.0;
		nmean = 0;
	}
	for (i = -1; i <= elev_grid + 1; i++) {
		lat = latmin + i * dlat;
		double latidx = (lat - platmin) * elev_grid / (platmax - platmin);
		int lat0 = (int)floor(latidx);
		for (j = -1; j <= elev_grid + 1; j++) {
			lng = lngmin + j * dlng;
			double lngidx = (lng - plngmin) * elev_grid / (plngmax - plngmin);
			int lng0 = (int)floor(lngidx);

			std::int16_t* eptr = pelev_base + lat0 * elev_stride + lng0;
			if (mode == 1) { // linear interpolation

				double w_lat = latidx - lat0;
				double w_lng = lngidx - lng0;
				e = (1.0 - w_lat) * (eptr[0] * (1.0 - w_lng) + eptr[1] * w_lng) + w_lat * (eptr[elev_stride] * (1.0 - w_lng) + eptr[elev_stride + 1] * w_lng);

			}
			else { // cubic spline interpolation

			 // take care of boundaries
				int latstencil[4] = { -elev_stride,0,elev_stride,2 * elev_stride };
				int lngstencil[4] = { -1,0,1,2 };
				if (lat0 < 0) latstencil[0] = 0;
				else if (lat0 >= elev_grid) latstencil[3] = elev_stride;
				if (lng0 < 0) lngstencil[0] = 0;
				else if (lng0 >= elev_grid) lngstencil[3] = 1;

				double a_m1, a_0, a_p1, a_p2, b_m1, b_0, b_p1, b_p2;
				double tlat = latidx - lat0;
				double tlng = lngidx - lng0;
				a_m1 = eptr[latstencil[0] + lngstencil[0]];
				a_0 = eptr[latstencil[0] + lngstencil[1]];
				a_p1 = eptr[latstencil[0] + lngstencil[2]];
				a_p2 = eptr[latstencil[0] + lngstencil[3]];
				b_m1 = 0.5 * (2.0 * a_0 + tlng * (-a_m1 + a_p1) +
					tlng * tlng * (2.0 * a_m1 - 5.0 * a_0 + 4.0 * a_p1 - a_p2) +
					tlng * tlng * tlng * (-a_m1 + 3.0 * a_0 - 3.0 * a_p1 + a_p2));
				a_m1 = eptr[latstencil[1] + lngstencil[0]];
				a_0 = eptr[latstencil[1] + lngstencil[1]];
				a_p1 = eptr[latstencil[1] + lngstencil[2]];
				a_p2 = eptr[latstencil[1] + lngstencil[3]];
				b_0 = 0.5 * (2.0 * a_0 + tlng * (-a_m1 + a_p1) +
					tlng * tlng * (2.0 * a_m1 - 5.0 * a_0 + 4.0 * a_p1 - a_p2) +
					tlng * tlng * tlng * (-a_m1 + 3.0 * a_0 - 3.0 * a_p1 + a_p2));
				a_m1 = eptr[latstencil[2] + lngstencil[0]];
				a_0 = eptr[latstencil[2] + lngstencil[1]];
				a_p1 = eptr[latstencil[2] + lngstencil[2]];
				a_p2 = eptr[latstencil[2] + lngstencil[3]];
				b_p1 = 0.5 * (2.0 * a_0 + tlng * (-a_m1 + a_p1) +
					tlng * tlng * (2.0 * a_m1 - 5.0 * a_0 + 4.0 * a_p1 - a_p2) +
					tlng * tlng * tlng * (-a_m1 + 3.0 * a_0 - 3.0 * a_p1 + a_p2));
				a_m1 = eptr[latstencil[3] + lngstencil[0]];
				a_0 = eptr[latstencil[3] + lngstencil[1]];
				a_p1 = eptr[latstencil[3] + lngstencil[2]];
				a_p2 = eptr[latstencil[3] + lngstencil[3]];
				b_p2 = 0.5 * (2.0 * a_0 + tlng * (-a_m1 + a_p1) +
					tlng * tlng * (2.0 * a_m1 - 5.0 * a_0 + 4.0 * a_p1 - a_p2) +
					tlng * tlng * tlng * (-a_m1 + 3.0 * a_0 - 3.0 * a_p1 + a_p2));
				e = 0.5 * (2.0 * b_0 + tlat * (-b_m1 + b_p1) +
					tlat * tlat * (2.0 * b_m1 - 5.0 * b_0 + 4.0 * b_p1 - b_p2) +
					tlat * tlat * tlat * (-b_m1 + 3.0 * b_0 - 3.0 * b_p1 + b_p2));
				e = max(-32767.0, min(32766.0, e));
			}
			plat0 = lat0;
			plng0 = lng0;
			elev_base[i * elev_stride + j] = (std::int16_t)e;
			if (emean && i >= 0 && j >= 0 && i <= elev_grid && j <= elev_grid) {
				*emean += e;
				nmean++;
			}
		}
	}
	if (emean && nmean)
		*emean /= nmean;
}
