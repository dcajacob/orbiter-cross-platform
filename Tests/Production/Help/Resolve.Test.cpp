// Licensed under the MIT License
#include "Production/NativeHelp.h"
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <sys/wait.h>
#include <thread>
using namespace orbiter::production;
void require(bool ok,const char* message) {if(!ok)throw std::runtime_error(message);}
int main(int argc,char** argv) {
    try {
        require(argc==2,"Expected staged resource root");
        ResourceResolver files(argv[1]);
        const auto first=NativeHelpUrl(files,"HTML\\Orbiter.CHM","/MainMenu.HTM#section");
        require(first.find("?topic=mainmenu.htm%23section")!=std::string::npos,"Case/slash/fragment adaptation failed");
        require(NativeHelpUrl(files,"html/orbiter.chm","/html/mfd.htm").find("?topic=mfd.htm")!=std::string::npos,"Legacy CHM topic prefix failed");
        require(NativeHelpUrl(files,"","").find("?topic=intro.htm")!=std::string::npos,"Original default topic differs");
        require(NativeContextHelpUrl(files,"DG-S,DG-S",true).find("?topic=dg-s.htm")!=std::string::npos,"Vessel help metadata failed");
        require(NativeContextHelpUrl(files,"Default\\Checklists\\Quickstart,Quickstart",false).find("?topic=quickstart.htm")!=std::string::npos,"Scenario help metadata failed");
        int rejected=0;
        for(const char* topic:{"../intro.htm","/../../intro.htm","nosuch.htm","_catalog.js","file:///etc/passwd","intro.htm?x=1"}) {
            try {NativeHelpUrl(files,"html/orbiter.chm",topic);}catch(const std::exception&) {++rejected;}
        }
        require(rejected==6,"Invalid/missing help topic accepted");
        bool missing=false;
        try {NativeHelpUrl(files,"html/missing.chm","");}catch(const std::exception&) {missing=true;}
        require(missing,"Missing book silently replaced");
        int books=0;std::ifstream catalog(files.Resolve("Help/catalog.tsv"));std::string row;
        while(std::getline(catalog,row)) {
            auto key=row.substr(0,row.find('\t'));
            require(NativeHelpUrl(files,key,"").find("file://")==0,"Book default cannot be resolved");++books;
        }
        require(books>=21,"Stock help catalog incomplete");
        require(PollNativeHelp().empty(),"Empty help service reports a launcher error");
        std::cout<<"Resolved "<<books<<" stock help entries; defaults, contexts, case, fragments, and missing/invalid topics checked\n";
    }catch(const std::exception& error){std::cerr<<error.what()<<'\n';return 1;}
}
