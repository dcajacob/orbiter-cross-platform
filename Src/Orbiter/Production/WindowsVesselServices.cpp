// Licensed under the MIT License
#include "WindowsVesselServices.h"
#include "Orbiter.h"
#include "Log.h"
#include "Pane.h"
#include "GraphicsAPI.h"
#include "State.h"
#include "Vessel.h"
#include "Camera.h"
extern Orbiter* g_pOrbiter;
extern Pane* g_pane;
extern Vessel* g_focusobj;
extern Camera* g_camera;
namespace orbiter::production {
namespace {
class WindowsVesselServices final:public VesselServices {
public:
    std::filesystem::path ConfigFile(const char* name,bool extension) override
    {return extension?g_pOrbiter->ConfigPath(name):g_pOrbiter->Cfg()->ConfigPathNoext(name);}
    void Fatal(const char* message) override
    {LOGOUT_ERR("%s",message);g_pOrbiter->TerminateOnError();}
    void Check(bool valid,const char* message) override {dCHECK(valid,message)}
    MeshManager& Meshes() override {return g_pOrbiter->meshmanager;}
    const char* PlaybackDirectory() const override {return g_pOrbiter->PState()->PlaybackDir();}
    void SetWarpFactor(double warp) override {g_pOrbiter->SetWarpFactor(warp);}
    double TimejumpDelta() const override {return g_pOrbiter->tjump.dt;}
    void RedrawCockpitAreas(int flags) override {g_pane->RedrawCockpitAreas(flags);}
    const double* ParticleLevel(const oapi::ParticleStream* stream) const override {return stream->Level();}
    void InsertVessel(Vessel* vessel) override {g_pOrbiter->InsertVessel(vessel);}
    double ManualControl(THGROUP_TYPE group,UInt32 device) const override {return g_pOrbiter->ManCtrlLevel(group,device);}
    void NotifyJump(const Vessel& vessel,const Vector& delta) override {g_pOrbiter->NotifyObjectJump(&vessel,delta);}
    void ShiftCockpit(const Vessel& vessel,const Vector& delta) override
    {if(g_pane && g_focusobj==&vessel) g_pane->ShiftVC(delta);}
    std::filesystem::path RecorderFile(const char* relative,bool) override {return relative;}
    void PlaybackWarp(double warp,double delay) override {g_pOrbiter->SetWarpFactor(warp,true,delay);}
    void RecallCameraPreset(int index) override {g_camera->RecallPreset(index);}
    void EndPlayback() override {g_pOrbiter->EndPlayback();}
    void PlaybackNote(char* s) override
    {
				oapi::ScreenAnnotation *sa = g_pOrbiter->SNotePB();
				if (sa) {
					if (!strcmp (s+4, "COL")) {
						double r, g, b;
						sscanf (s+8, "%lf%lf%lf", &r, &g, &b);
						VECTOR3 col = {r,g,b};
						sa->SetColour (col);
					} else if (!strcmp (s+4, "SIZE")) {
						double scale;
						sscanf (s+9, "%lf", &scale);
						sa->SetSize (scale);
					} else if (!strcmp (s+4, "POS")) {
						double x1, y1, x2, y2;
						sscanf (s+8, "%lf%lf%lf%lf", &x1, &y1, &x2, &y2);
						sa->SetPosition (x1, y1, x2, y2);
					} else if (!strcmp (s+4, "OFF")) {
						sa->ClearText();
					} else {
						sa->SetText (s+5);
					}
				}
    }
};
}
VesselServices& GetWindowsVesselServices() {static WindowsVesselServices services;return services;}
}
