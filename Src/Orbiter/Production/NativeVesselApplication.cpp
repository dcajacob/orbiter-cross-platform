// Licensed under the MIT License
// Services unavailable in the production headless host. These fail explicitly
// when requested; no native cockpit/particle implementation is claimed here.
#include "Vessel.h"
#include "Config.h"
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
oapi::ParticleStream* Vessel::AddParticleStream(PARTICLESTREAMSPEC*,const Vector&,const Vector&,double*)
{if(noParticles()) return nullptr;unavailable("particle streams");}
oapi::ParticleStream* Vessel::AddExhaustStream(ThrustSpec*,PARTICLESTREAMSPEC*,const Vector*,const Vector*)
{if(noParticles()) return nullptr;unavailable("exhaust particle streams");}
oapi::ParticleStream* Vessel::AddReentryStream(PARTICLESTREAMSPEC*)
{if(noParticles()) return nullptr;unavailable("reentry particle streams");}
bool Vessel::DelExhaustStream(oapi::ParticleStream*)
{if(!ncontrail) return false;unavailable("exhaust particle removal");}
bool Vessel::DelReentryStream(oapi::ParticleStream*)
{if(!nreentrystream) return false;unavailable("reentry particle removal");}
void Vessel::ClearExhaustStreamDefinitions()
{if(ncontrail) unavailable("exhaust particle removal");}
void Vessel::ClearReentryStreams()
{if(nreentrystream) unavailable("reentry particle removal");}
