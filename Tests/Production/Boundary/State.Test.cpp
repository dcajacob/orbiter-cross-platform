// Licensed under the MIT License
#include "State.h"
#include "Production/ScenarioColor.h"
#include <cmath>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <vector>
#include <algorithm>
#include <iomanip>
void require(bool condition,const char* message) { if (!condition) throw std::runtime_error(message); }
int main(int argc,char** argv)
{
    try {
        require(argc==3,"Expected original stock scenario root and metadata output");
        State state(60000.25);
        require(state.Mjd()==60000.25 && std::string(state.Solsys())=="Sol","Explicit initial epoch changed");
        std::istringstream fixture("BEGIN_ENVIRONMENT\r\n  System Sol ; comment\r\n  Date JD 2451545.0\r\n  Context Test\\Context\r\n  SplashScreen #123456 Textures\\splash.dds\r\n  Script Tests\\control.lua\r\n  Help help/index.htm\r\n  Playback Recorded\\flight\r\nEND_ENVIRONMENT\r\nBEGIN_FOCUS\r\n  Ship PB\r\nEND_FOCUS\r\n");
        require(state.Read(fixture,"sample.scn",61000),"Original scenario environment parse failed");
        require(state.Mjd()==51544.5 && std::string(state.Focus())=="PB","JD or focus interpretation changed");
        require(std::string(state.Context())=="Test\\Context" && std::string(state.Script())=="Tests\\control.lua",
            "Context/script fields changed");
        require(state.SplashColor()==0x563412 && std::string(state.SplashScreen())=="Textures\\splash.dds",
            "Splash colour or Windows-style source path changed");
        require(std::string(state.PlaybackDir())=="Recorded\\flight" && std::string(state.ScnHelp())=="help/index.htm",
            "Playback/help fields changed");
        state.Update(61344.12345678912,"ISS");
        std::ostringstream saved;state.Write(saved,"First\r\nSecond",0);
        require(saved.str().find("  Date MJD 61344.1234567891\n")!=std::string::npos && saved.str().find('\r')==std::string::npos,
            "Original save precision or description line conversion changed");
        std::istringstream reload(saved.str());State restored(1);
        require(restored.Read(reload,"saved.scn",2) && restored.Mjd()==61344.1234567891 && std::string(restored.Focus())=="ISS",
            "Production environment round trip changed");
        std::istringstream je("BEGIN_ENVIRONMENT\n System Sol\n Date JE 2000\nEND_ENVIRONMENT\n");
        require(state.Read(je,"epoch.scn",3) && state.Mjd()==51544.5,"Julian epoch interpretation changed");
        std::istringstream today("BEGIN_ENVIRONMENT\n System Sol\n Date MJD Today\nEND_ENVIRONMENT\n");
        require(state.Read(today,"Today.scn",61234.5) && state.Mjd()==61234.5 && !state.Script() && !state.Context(),
            "Default epoch or reset behavior changed");
        require(GetCSSColor("ReD")==255 && GetCSSColor("invalid")==0xff00ff,"Original named colour conversion changed");
        const auto root=std::filesystem::absolute(argv[1]);
        const auto output=std::filesystem::absolute(argv[2]);
        std::filesystem::create_directories(output.parent_path());
        std::ofstream manifest(output,std::ios::binary);
        require(bool(manifest),"Cannot write metadata manifest");
        manifest.imbue(std::locale::classic());manifest<<std::setprecision(17);
        manifest<<"scenario,mjd,system,context,focus,script,splash,splash_color,help,playback\n";
        const auto quoted=[&](const char* value) {
            manifest<<'"';
            if (value) for (const char* c=value;*c;++c) { if (*c=='"') manifest<<'"';manifest<<*c; }
            manifest<<'"';
        };
        std::vector<std::filesystem::path> files;
        for (const auto& file:std::filesystem::recursive_directory_iterator(root))
            if (file.is_regular_file() && file.path().extension()==".scn") files.push_back(file.path().lexically_relative(root));
        std::sort(files.begin(),files.end(),[](const auto& a,const auto& b) { return a.generic_string()<b.generic_string(); });
        std::size_t count=0;
        for (const auto& file:files) {
            State stock(61344.5);
            std::ifstream input(root/file);
            require(bool(input) && stock.Read(input,file.generic_string(),61344.5),"Stock environment read failed");
            require(std::isfinite(stock.Mjd()) && std::string(stock.Solsys())=="Sol","Stock epoch or real system name lost");
            quoted(file.generic_string().c_str());manifest<<','<<stock.Mjd()<<',';quoted(stock.Solsys());manifest<<',';
            quoted(stock.Context());manifest<<',';quoted(stock.Focus());manifest<<',';quoted(stock.Script());manifest<<',';
            quoted(stock.SplashScreen());manifest<<','<<stock.SplashColor()<<',';quoted(stock.ScnHelp());manifest<<',';
            quoted(stock.PlaybackDir());manifest<<'\n';
            ++count;
        }
        manifest.close();require(bool(manifest),"Failed to finalize metadata manifest");
        require(count==157,"Pinned scenario metadata corpus changed");
        require(!state.Read(root/"MissingRequiredScenario.scn",61344.5),"Missing scenario was accepted");
        std::ifstream failed(root/"MissingRequiredScenario.scn");
        require(!state.Read(failed,"MissingRequiredScenario.scn",61344.5),"Failed input stream was accepted");
        std::cout<<"Original State environment/focus metadata read for "<<count<<" scenarios; explicit epoch, paths and stock precision passed. No world was initialized.\n";
        return 0;
    } catch (const std::exception& error) { std::cerr<<error.what()<<'\n'; return 1; }
}
