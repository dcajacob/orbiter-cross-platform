// Licensed under the MIT License
// Services unavailable in the production headless host. These fail explicitly
// when requested; no native cockpit/particle implementation is claimed here.
#include "Vessel.h"
#include "Config.h"
#include "NativeGraphics.h"
#include "NativeParticle.h"
#include "RigidBodyServices.h"
#include "GeometryConversions.h"
#include "SurfaceServices.h"
#include <stdexcept>
using namespace orbiter::production;
namespace {
[[noreturn]] void unavailable(const char* feature)
{throw std::runtime_error(std::string("Native vessel service unavailable: ")+feature);}
bool noParticles()
{return !GetSurfaceServices().HasGraphics() || !GetSurfaceServices().Configuration().CfgVisualPrm.bParticleStreams;}
}
int Vessel::ConsumeBufferedKey(oapi::UInt32 key,bool down,char* state)
{
    if(modIntf.v->Version()>=1) {
        const int result=static_cast<VESSEL2*>(modIntf.v)->clbkConsumeBufferedKey(key,down,state);
        if(result) return result;
    }
    if(!down) return 0;
    unavailable("default buffered flight keys");
}
void Vessel::DrawHUD(HUD*,oapi::Sketchpad*) {unavailable("HUD drawing");}
void Vessel::RenderHUD(HUD*,int,HUDPAINTSPEC*,SURFHANDLE) {unavailable("HUD rendering");}
int Vessel::RegisterMFDMode(const MFDMODESPECEX*) {unavailable("MFD registration");}
bool Vessel::UnregisterMFDMode(int)
{if(!nmfdmode) return false;unavailable("MFD removal");}
void Vessel::UnregisterMFDModes()
{if(nmfdmode) unavailable("MFD removal");}
bool Vessel::LoadPanel2D(int,Panel2D*) const {unavailable("2D panels");}
void Vessel::LeanCamera(int,bool) {unavailable("cockpit camera movement");}
void Vessel::UndockInteractive(const Vessel* exclude,double separation)
{
    if(ndock==1) Undock(0,exclude,separation);
    else if(ndock) unavailable("docking-port selection");
}
oapi::ParticleStream *Vessel::AddParticleStream (PARTICLESTREAMSPEC *pss, const Vector &pos, const Vector &dir, double *lvl)
{
	if (!GetSurfaceServices().Configuration().CfgVisualPrm.bParticleStreams) return 0;
	NativeGraphics *gc = (GetSurfaceServices().HasGraphics()?GetNativeRenderContext().graphics:nullptr);
	if (!gc) return 0;

	oapi::ParticleStream **tmp = new oapi::ParticleStream*[ncontrail+1]; GetRigidBodyServices().TraceAllocation(__FILE__,__LINE__);
	if (ncontrail) {
		memcpy (tmp, contrail, ncontrail*sizeof(oapi::ParticleStream*));
		delete []contrail;
	}
	contrail = tmp;
	contrail[ncontrail] = gc->Exhaust (pss, (OBJHANDLE)this, lvl, MakeVECTOR3(pos), MakeVECTOR3(-dir));
	return contrail[ncontrail++];
}
oapi::ParticleStream *Vessel::AddExhaustStream (ThrustSpec *ts, PARTICLESTREAMSPEC *pss, const Vector *pos, const Vector *dir)
{
	if (!GetSurfaceServices().Configuration().CfgVisualPrm.bParticleStreams) return 0;
	NativeGraphics *gc = (GetSurfaceServices().HasGraphics()?GetNativeRenderContext().graphics:nullptr);
	if (!gc) return 0;

	oapi::ParticleStream **tmp = new oapi::ParticleStream*[ncontrail+1]; GetRigidBodyServices().TraceAllocation(__FILE__,__LINE__);
	if (ncontrail) {
		memcpy (tmp, contrail, ncontrail*sizeof(oapi::ParticleStream*));
		delete []contrail;
	}
	contrail = tmp;
	contrail[ncontrail] = gc->Exhaust (pss, (OBJHANDLE)this, &ts->level, &ts->ref, &ts->dir);
	if (pos) // local position reference
		contrail[ncontrail]->SetFixedPos (MakeVECTOR3(*pos));
	if (dir) // local direction reference
		contrail[ncontrail]->SetFixedDir (MakeVECTOR3(*dir));
	return contrail[ncontrail++];
}
oapi::ParticleStream *Vessel::AddReentryStream (PARTICLESTREAMSPEC *pss)
{
	if (!GetSurfaceServices().Configuration().CfgVisualPrm.bParticleStreams) return 0;
	NativeGraphics *gc = (GetSurfaceServices().HasGraphics()?GetNativeRenderContext().graphics:nullptr);
	if (!gc) return 0;

	oapi::ParticleStream **tmp = new oapi::ParticleStream*[nreentrystream+1]; GetRigidBodyServices().TraceAllocation(__FILE__,__LINE__);
	if (nreentrystream) {
		memcpy (tmp, reentrystream, nreentrystream*sizeof(oapi::ParticleStream*));
		delete []reentrystream;
	}
	reentrystream = tmp;
	reentrystream[nreentrystream] = gc->Reentry (pss, (OBJHANDLE)this);
	return reentrystream[nreentrystream++];
}
bool Vessel::DelExhaustStream (oapi::ParticleStream *ep)
{
	if (!ncontrail) return false;

	oapi::UInt32 i, j, k;
	for (i = 0; i < ncontrail; i++)
		if (contrail[i] == ep) break;
	if (i == ncontrail) return false;

	ep->Detach();
	// we detach the contrail from its source, but leave it
	// to the scene to delete it once all particles have expired

	oapi::ParticleStream **tmp;
	if (ncontrail > 1) {
		tmp = new oapi::ParticleStream*[ncontrail-1]; GetRigidBodyServices().TraceAllocation(__FILE__,__LINE__);
		for (j = k = 0; j < ncontrail; j++)
			if (j != i) tmp[k++] = contrail[j];
	} else tmp = 0;
	delete []contrail;
	contrail = tmp;
	ncontrail--;
	return true;
}
bool Vessel::DelReentryStream (oapi::ParticleStream *ep)
{
	if (!nreentrystream) return false;

	oapi::UInt32 i, j, k;

	for (i = 0; i < nreentrystream; i++)
		if (reentrystream[i] == ep) break;
	if (i == nreentrystream) return false;

	ep->Detach();
	// we detach the contrail from its source, but leave it
	// to the scene to delete it once all particles have expired

	oapi::ParticleStream **tmp;
	if (nreentrystream > 1) {
		tmp = new oapi::ParticleStream*[nreentrystream-1]; GetRigidBodyServices().TraceAllocation(__FILE__,__LINE__);
		for (j = k = 0; j < nreentrystream; j++)
			if (j != i) tmp[k++] = reentrystream[j];
	} else tmp = 0;
	delete []reentrystream;
	reentrystream = tmp;
	nreentrystream--;
	return true;
}
void Vessel::ClearExhaustStreamDefinitions ()
{
	if (ncontrail) {
		for (oapi::UInt32 i = 0; i < ncontrail; i++) contrail[i]->Detach();
		delete []contrail;
		contrail = NULL;
		ncontrail = 0;
	}
}
void Vessel::ClearReentryStreams ()
{
	if (nreentrystream) {
		for (oapi::UInt32 i = 0; i < nreentrystream; i++)
			reentrystream[i]->Detach();
		delete []reentrystream;
		reentrystream = NULL;
		nreentrystream = 0;
	}
}
