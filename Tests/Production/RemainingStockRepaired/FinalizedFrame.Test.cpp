// Licensed under the MIT License
// Evidence policy controls only; actual framebuffer/tick correlation is tested separately.
#include "../../../OVP/OGLClient/FinalizedFrameCapture.h"
#include <iostream>
#include <sstream>
#include <vector>

namespace {
unsigned current=0;
unsigned read(unsigned abi) {if(abi!=2)throw std::runtime_error("Caller used wrong observer ABI");return current;}
unsigned wrongAbi(unsigned) {return (std::numeric_limits<unsigned>::max)();}
void require(bool value,const char* message) {if(!value)throw std::runtime_error(message);}
}
int main(int argc,char** argv) {
    try {
        require(argc==2,"Fresh control directory required");const std::filesystem::path root(argv[1]);
        require(!std::filesystem::exists(root),"Control directory exists");std::filesystem::create_directories(root);
        using Policy=Evidence::FinalizedFrameCapture;
        Policy legacy;legacy.Begin(root);require(!legacy.Enabled(),"Absent marker changed legacy mode");
        std::ostringstream untouched;legacy.Summary(untouched);require(untouched.str().empty(),"Legacy summary changed");
        auto folder=root/"valid";std::filesystem::create_directories(folder);
        std::ofstream(folder/Policy::Marker())<<Policy::Protocol()<<" 800\n";
        Policy policy;policy.Begin(folder);require(policy.Enabled(),"Valid descriptor did not enable mode");
        for(unsigned tick:{0u,1u,355u,360u,799u}){current=tick;require(!policy.Select(read),"Captured before finalized target");}
        current=800;require(policy.Select(read),"Finalized target was not selected");
        std::ostringstream summary;policy.Summary(summary);
        require(summary.str()==",\"capture_protocol\":\"remaining-stock-matched-clock-v2\",\"finalized_tick\":800","Selected clock metadata differs");
        unsigned rejected=0;
        auto reject=[&](auto action){try{action();}catch(const std::exception&){++rejected;return;}throw std::runtime_error("Invalid evidence policy accepted");};
        current=801;reject([&]{policy.Select(read);});
        reject([&]{policy.Select(nullptr);});reject([&]{policy.Select(wrongAbi);});
        const std::vector<std::string> damaged={"foreign-protocol 800\n","remaining-stock-matched-clock-v2 0\n",
            "remaining-stock-matched-clock-v2 -1\n","remaining-stock-matched-clock-v2 10000001\n",
            "remaining-stock-matched-clock-v2 800 extra\n","remaining-stock-matched-clock-v2\n"};
        for(unsigned i=0;i<damaged.size();++i) {
            auto path=root/("damaged-"+std::to_string(i));std::filesystem::create_directories(path);
            std::ofstream(path/Policy::Marker())<<damaged[i];reject([&]{Policy value;value.Begin(path);});
        }
        require(rejected==9,"Incomplete policy controls");
        std::cout<<"{\"status\":\"passed\",\"legacy_unchanged\":true,\"selected_finalized_tick\":800,\"rejected_controls\":"<<rejected<<"}\n";
        return 0;
    }catch(const std::exception& error){std::cerr<<error.what()<<'\n';return 1;}
}
