// Licensed under the MIT License
// Recorded SDK inputs and read-only observations of the original Windows app.
#define ORBITER_MODULE
#include "Orbitersdk.h"
#include "ApplicationObservation.h"
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <limits>
#include <locale>
#include <stdexcept>
#include <string>
#include <vector>
#include <cmath>
#include <cstring>
namespace {
using SetObserver=int(*)(unsigned,OrbiterTestObserver,double);
class Driver;
Driver* driver=nullptr;
void observe(const char*,const char*,double,double,int);
void require(bool ok,const char* message){if(!ok)throw std::runtime_error(message);}
class Driver final:public oapi::Module {
    SetObserver setter=nullptr;
    struct Action {unsigned tick;std::string event,coordinates;VECTOR3 point;};
    std::vector<Action> actions;
    std::ofstream state,events,inputs,landmarks;
    HWND window=nullptr;
    void mouse(const Action& action) {
        DWORD width=0,height=0;oapiGetViewportSize(&width,&height);
        require(width==1280 && height==720,"Control reference viewport differs");
        VECTOR3 projected=action.point;
        int x=0,y=0;
        if(action.coordinates=="local") {
            auto* v=oapiGetFocusInterface();VECTOR3 global{},camera{};MATRIX3 rotation{};
            v->Local2Global(action.point,global);oapiCameraGlobalPos(&camera);oapiCameraRotationMatrix(&rotation);
            projected=tmul(rotation,global-camera);
            require(projected.z>0,"Required actual VC click point is behind the camera");
            const double scale=.5*height/std::tan(oapiCameraAperture());
            x=int(std::lround(.5*width-.5+projected.x*scale/projected.z));
            y=int(std::lround(.5*height-.5-projected.y*scale/projected.z));
        } else {
            require(action.coordinates=="pixel","Unknown recorded mouse coordinate system");
            x=int(action.point.x);y=int(action.point.y);
        }
        require(x>=0 && x<int(width) && y>=0 && y<int(height),"Required actual cockpit control is outside the viewport");
        const UINT message=action.event=="left_down"?WM_LBUTTONDOWN:WM_LBUTTONUP;
        require(action.event=="left_down" || action.event=="left_up","Unknown recorded mouse event");
        // Route through the actual owned render-window procedure and Pane's
        // original 2D/VC hit testing. Do not invoke a vessel callback directly.
        SendMessageW(window,WM_MOUSEMOVE,0,MAKELPARAM(x,y));
        inputs<<frames<<",move,"<<x<<','<<y<<'\n';
        SendMessageW(window,message,message==WM_LBUTTONDOWN?MK_LBUTTON:0,MAKELPARAM(x,y));
        inputs<<frames<<','<<action.event<<','<<x<<','<<y<<'\n';inputs.flush();
        landmarks<<frames<<','<<action.coordinates<<','<<action.point.x<<','<<action.point.y<<','<<action.point.z
            <<','<<projected.x<<','<<projected.y<<','<<projected.z<<','<<x<<','<<y<<'\n';landmarks.flush();
    }
    std::string target;
    unsigned frames=0,total=0;int cockpit=0,left=0,right=0,hud=0;
    bool started=false,initialized=false;
    template<class F>void guarded(F action){try{action();}catch(const std::exception& e){std::ofstream("cockpit-failure.txt")<<e.what()<<'\n';std::exit(42);}}
    void snapshot(){
        auto* v=oapiGetFocusInterface();require(v && target==v->GetName(),"Cockpit focus differs from required real vessel");
        VECTOR3 p{},velocity{},omega{};MATRIX3 rotation{};v->GetGlobalPos(p);v->GetGlobalVel(velocity);v->GetAngularVel(omega);v->GetRotationMatrix(rotation);
        state<<frames<<','<<oapiGetSimTime()<<','<<oapiGetSimMJD()<<','<<v->GetName()<<','<<v->GetClassName()<<','<<oapiCockpitMode()<<','<<oapiGetHUDMode()<<','<<oapiGetMFDMode(0)<<','<<oapiGetMFDMode(1);
        for(double value:{p.x,p.y,p.z,velocity.x,velocity.y,velocity.z,rotation.m11,rotation.m12,rotation.m13,rotation.m21,rotation.m22,rotation.m23,rotation.m31,rotation.m32,rotation.m33,omega.x,omega.y,omega.z,v->GetMass(),v->GetFuelMass()})state<<','<<value;
        state<<','<<v->GetMeshCount()<<','<<v->GetThrusterCount()<<','<<v->GetAttitudeMode()<<'\n';state.flush();
        require(v->GetAttitudeMode()==(frames>=11 && frames<=30?2:1),"Actual window input did not select the expected real vessel RCS mode");
    }
public:
    explicit Driver(HINSTANCE instance):Module(instance){guarded([&]{
        std::ifstream input("cockpit-case.txt");require(bool(input>>target>>total>>cockpit>>left>>right>>hud),"Invalid cockpit fixture controls");
        require(total==60 && cockpit>=1 && cockpit<=3 && left>=1 && left<=10 && right>=1 && right<=10,"Unsupported cockpit control schedule");
        for(auto* stream:{&state,&events,&inputs,&landmarks}){stream->imbue(std::locale::classic());stream->exceptions(std::ios::badbit|std::ios::failbit);}
        state.open("cockpit-state.csv");events.open("cockpit-events.csv");inputs.open("control-inputs.csv");landmarks.open("control-landmarks.csv");state<<std::setprecision(17);events<<std::setprecision(17);landmarks<<std::setprecision(17);
        state<<"tick,seconds,mjd,object,class,cockpit,hud,left_mfd,right_mfd,x,y,z,vx,vy,vz,m11,m12,m13,m21,m22,m23,m31,m32,m33,wx,wy,wz,mass,fuel,meshes,thrusters,rcs_mode\n";
        events<<"tick,seconds,mjd,phase,object,running\n";
        inputs<<"tick,event,x,y\n";landmarks<<"tick,coordinates,local_x,local_y,local_z,view_x,view_y,view_z,x,y\n";
        std::ifstream schedule("control-schedule.txt");unsigned count=0;require(bool(schedule>>count) && count==4,"Incomplete original control schedule");
        for(unsigned index=0;index<count;++index){Action action{};require(bool(schedule>>action.tick>>action.event>>action.coordinates>>action.point.x>>action.point.y>>action.point.z),"Invalid original mouse input");actions.push_back(action);}
        setter=reinterpret_cast<SetObserver>(GetProcAddress(GetModuleHandleW(nullptr),"OrbiterTestSetObserver"));require(setter && setter(1,observe,51982.5),"Original observation ABI missing");std::srand(0);
    });}
    ~Driver()override{if(setter)setter(1,nullptr,std::numeric_limits<double>::quiet_NaN());}
    void clbkSimulationStart(RenderMode mode)override{guarded([&]{
        require(mode!=RENDER_NONE,"Real graphics client required");auto* v=oapiGetFocusInterface();require(v && v->GetThrusterCount()>0 && v->GetMeshCount()>0,"Actual stock vessel required");
        started=true;
    });}
    void clbkPreStep(double,double,double)override{guarded([&]{
        // The stock MFD scheduler limits real-time refresh to 10Hz. Pace these
        // software-rendered fixtures above that bound without altering clocks,
        // calculations, integrators or the original instrumentation scheduler.
        Sleep(120);
        // Original Orbiter initializes Pane after clbkSimulationStart. The
        // first pre-step is the first SDK control point with a complete panel.
        if(!initialized){
            require(oapiCameraInternal() && oapiCockpitMode()==cockpit,"Scenario cockpit failed to initialize");
            window=FindWindowA("Orbiter Render Window",nullptr);DWORD process=0;
            require(window && GetWindowThreadProcessId(window,&process) && process==GetCurrentProcessId(),"Required owned real Orbiter render window missing");
            RECT client{};require(GetClientRect(window,&client) && client.right==1280 && client.bottom==720,"Actual client dimensions differ");
            std::ofstream environment("control-environment.json");
            environment<<"{\"desktop_width\":"<<GetSystemMetrics(SM_CXSCREEN)<<",\"desktop_height\":"<<GetSystemMetrics(SM_CYSCREEN)<<",\"viewport_width\":1280,\"viewport_height\":720,\"msvc\":"<<_MSC_VER<<"}\n";
            oapiOpenMFD(left,0);oapiOpenMFD(right,1);oapiSetHUDMode(hud);initialized=true;snapshot();
        }
        for(const auto& action:actions)if(action.tick==frames)mouse(action);
    });}
    void core(const char* phase,const char* object,double seconds,double mjd,int running){guarded([&]{
        events<<frames<<','<<seconds<<','<<mjd<<','<<phase<<','<<object<<','<<running<<'\n';
        if(started && std::string(phase)=="app.frame.end"){
            require(initialized,"Original frame completed before cockpit setup");
            require(running!=0,"Unexpected paused reference frame");++frames;snapshot();
            require(oapiCameraInternal() && oapiCockpitMode()==cockpit,"Original requested cockpit did not initialize");
            require(oapiGetMFDMode(0)==left && oapiGetMFDMode(1)==right,"Original stock instruments did not initialize");
        }
    });}
    void clbkSimulationEnd()override{guarded([&]{require(frames==total,"Incomplete cockpit reference run");started=false;events.flush();state.flush();std::ofstream("cockpit-complete.txt")<<frames<<'\n';});}
};
void observe(const char* phase,const char* object,double seconds,double mjd,int running){if(driver)driver->core(phase,object,seconds,mjd,running);}
}
DLLCLBK void InitModule(HINSTANCE instance){driver=new Driver(instance);oapiRegisterModule(driver);}
DLLCLBK void ExitModule(HINSTANCE){delete driver;driver=nullptr;}
