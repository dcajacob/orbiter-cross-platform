// Licensed under the MIT License
#include "NativeWorldVesselServices.h"
#include "Vessel.h"
#include "SuperVessel.h"
#include "VesselServices.h"
#include "Text.h"
#include <stdexcept>
namespace orbiter::production {
namespace {
void PreflightPlayback(std::ifstream& input,const char* name) {
    // A missing required stock position stream is a native resource error.
    // Resolve it before entering Vessel's original constructor, whose legacy
    // raw allocations cannot unwind a throwing host resource lookup. Retain
    // the stream position and every original status/physics operation.
    const auto position=input.tellg();
    if(position==std::streampos(-1))throw std::runtime_error("Vessel scenario stream is not seekable");
    bool requested=false;std::string line;
    while(std::getline(input,line)) {
        const auto start=line.find_first_not_of(" \t\r");
        if(start==std::string::npos)continue;
        const auto end=line.find_last_not_of(" \t\r");
        const auto value=line.substr(start,end-start+1);
        if(!CompareText(value.c_str(),"END"))break;
        if(!ComparePrefix(value.c_str(),"FLIGHTDATA",10)) {requested=true;break;}
    }
    input.clear();input.seekg(position);
    if(!input)throw std::runtime_error("Cannot restore vessel scenario stream");
    if(requested) {
        auto& services=GetVesselServices();
        const std::string directory(services.PlaybackDirectory());
        const auto slash=directory.find_last_of("/\\");
        const auto relative="Flights/"+directory.substr(slash==std::string::npos?0:slash+1)+"/"+name+".pos";
        services.RecorderFile(relative.c_str(),false);
    }
}
class NativeWorldVesselServices final:public WorldVesselServices {
    bool& force;
public:
    explicit NativeWorldVesselServices(bool& value):force(value) {}
    Body& State(Vessel& vessel) const override {return vessel;}
    const char* Name(const Vessel& vessel) const override {return vessel.Name();}
    Vessel* Create(PlanetarySystem& system,const char* name,const char* type,std::ifstream& input) override
    {PreflightPlayback(input,name);return new Vessel(&system,name,type,input);}
    void PostCreation(Vessel& vessel) override {vessel.PostCreation();}
    void InitSupervessel(Vessel& vessel) override {vessel.InitSupervessel();}
    void ModulePostCreation(Vessel& vessel) override {vessel.ModulePostCreation();}
    void Write(const Vessel& vessel,std::ostream& output) override {vessel.Write(output);}
    void OptionChanged(Vessel& vessel,UInt32 category,UInt32 item) override {vessel.OptionChanged(category,item);}
    void UpdateBodyForces(Vessel& vessel) override {vessel.UpdateBodyForces();}
    void Update(Vessel& vessel,bool force) override {vessel.Update(force);}
    void PostUpdate(Vessel& vessel) override {vessel.PostUpdate();}
    void Timejump(Vessel& vessel,double seconds,int mode) override {vessel.Timejump(seconds,mode);}
    void ProcessMessage(Vessel& vessel,UInt32 message,void* data) override {vessel.ProcessMessage(message,data);}
    SuperVessel* Structure(Vessel& vessel) const override {return vessel.SuperStruct();}
    SuperVessel* CreateStructure(Vessel& a,Vessel& b,int pa,int pb,bool mix) override {return new SuperVessel(&a,&b,pa,pb,mix);}
    void DeleteStructure(SuperVessel* structure) override {delete structure;}
    void Merge(SuperVessel& structure,Vessel& a,int pa,Vessel& b,int pb) override {structure.Merge(&a,pa,&b,pb);}
    void Add(SuperVessel& structure,Vessel& a,int pa,Vessel& b,int pb,bool mix) override {structure.Add(&a,pa,&b,pb,mix);}
    void Detach(SuperVessel& structure,Vessel& vessel,int port,double speed) override {structure.Detach(&vessel,port,speed);}
    bool Empty(const SuperVessel& structure) const override {return !structure.nVessel();}
    void Update(SuperVessel& structure,bool force) override {structure.Update(force);}
    void PostUpdate(SuperVessel& structure) override {structure.PostUpdate();}
    void ForceUpdate() override {force=true;}
};
}
std::unique_ptr<WorldVesselServices> CreateNativeWorldVesselServices(bool& force)
{return std::make_unique<NativeWorldVesselServices>(force);}
}
