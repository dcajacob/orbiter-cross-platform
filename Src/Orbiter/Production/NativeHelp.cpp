// Licensed under the MIT License
#include "NativeHelp.h"
#include <cerrno>
#include <cstring>
#include <fstream>
#include <iostream>
#include <spawn.h>
#include <stdexcept>
#include <sys/wait.h>
#include <unistd.h>
extern char** environ;

namespace orbiter::production {
namespace {
// Desktop viewers may outlive a simulation session. Their launchers are owned
// at process scope, polled across sessions, and never killed on session exit.
struct Launchers {
    std::vector<pid_t> children;
    ~Launchers() { for(auto child:children) {int status; waitpid(child,&status,WNOHANG);} }
};
Launchers launchers;
struct SpawnActions {
    posix_spawn_file_actions_t value;
    SpawnActions() {
        int error=posix_spawn_file_actions_init(&value);
        if(error)throw std::runtime_error(std::strerror(error));
        // Linux/glibc: the external browser must not retain simulation logs,
        // recorder streams, module files, or graphics/display connections.
        error=posix_spawn_file_actions_addclosefrom_np(&value,3);
        if(error) {posix_spawn_file_actions_destroy(&value);throw std::runtime_error(std::strerror(error));}
    }
    ~SpawnActions() {posix_spawn_file_actions_destroy(&value);}
};
std::string Encode(const std::string& text,bool path=false) {
    static const char hex[]="0123456789ABCDEF";
    std::string result;
    for(unsigned char c:text) {
        if((c>='a'&&c<='z')||(c>='A'&&c<='Z')||(c>='0'&&c<='9')||c=='-'||c=='_'||c=='.'||c=='~'||(path&&c=='/'))result+=char(c);
        else {result+='%';result+=hex[c>>4];result+=hex[c&15];}
    }
    return result;
}
}
std::string NativeHelpUrl(const ResourceResolver& files,const std::string& requestedBook,const std::string& requestedTopic) {
    const auto book=ResourceResolver::Normalize(requestedBook.empty()?"html/orbiter.chm":requestedBook);
    std::ifstream catalog(files.Resolve("Help/catalog.tsv"));
    std::string row,viewer,topic;
    while(std::getline(catalog,row)) {
        if(!row.empty()&&row.back()=='\r')row.pop_back();
        const auto first=row.find('\t'),second=first==std::string::npos?first:row.find('\t',first+1);
        if(first==std::string::npos||second==std::string::npos)throw std::runtime_error("Invalid help catalog");
        if(row.substr(0,first)==book) {viewer=row.substr(first+1,second-first-1);topic=row.substr(second+1);break;}
    }
    if(viewer.empty())throw std::runtime_error("Help book is not installed: "+requestedBook);
    if(!requestedTopic.empty())topic=requestedTopic;
    while(!topic.empty()&&(topic.front()=='/'||topic.front()=='\\'))topic.erase(0,1);
    const auto hash=topic.find('#');
    const auto fragment=hash==std::string::npos?std::string():topic.substr(hash);
    auto name=ResourceResolver::Normalize(topic.substr(0,hash));
    const auto directory=std::filesystem::path(viewer).parent_path();
    auto exists=[&](const std::string& value){return files.Contains((directory/value).generic_string());};
    if(!exists(name)&&name.compare(0,5,"html/")==0)name.erase(0,5);
    if(!exists(name)&&std::filesystem::path(name).extension().empty())name+=".htm";
    const auto extension=std::filesystem::path(name).extension().string();
    if(extension!=".htm"&&extension!=".html")throw std::runtime_error("Invalid help topic: "+name);
    // Resolve the topic as well as the viewer: a missing page is a visible error,
    // never a silent fallback to an unrelated default page.
    files.Resolve((directory/name).generic_string());
    return "file://"+Encode(files.Resolve(viewer).generic_string(),true)+"?topic="+Encode(name+fragment);
}
std::string NativeContextHelpUrl(const ResourceResolver& files,const std::string& context,bool vessel) {
    if(context.empty())return {};
    const auto comma=context.find(',');
    auto book=context.substr(0,comma);
    const auto topic=comma==std::string::npos?std::string():context.substr(comma+1);
    if(std::filesystem::path(book).extension().empty())book+=".chm";
    return NativeHelpUrl(files,std::string("html/")+(vessel?"vessels/":"scenarios/")+book,topic);
}
void OpenNativeHelp(const std::string& url) {
    if(url.compare(0,7,"file://")!=0)throw std::invalid_argument("Help requires a local file URL");
    // Reserve before spawning so a failed allocation cannot lose child ownership.
    launchers.children.reserve(launchers.children.size()+1);
    char command[]="xdg-open";
    char* args[]={command,const_cast<char*>(url.c_str()),nullptr};
    // Simulator module/preload paths belong to this process, not the desktop
    // browser (which may have an entirely different runtime or sandbox).
    std::vector<char*> environment;
    for(char** entry=environ;*entry;++entry)
        if(std::strncmp(*entry,"LD_LIBRARY_PATH=",16)!=0&&std::strncmp(*entry,"LD_PRELOAD=",11)!=0)environment.push_back(*entry);
    environment.push_back(nullptr);
    SpawnActions actions;
    pid_t child=0;
    const int error=posix_spawnp(&child,command,&actions.value,nullptr,args,environment.data());
    if(error)throw std::runtime_error(std::string("Cannot open desktop help: ")+std::strerror(error));
    launchers.children.push_back(child);
    std::clog<<"Opened help: "<<url<<'\n';
}
std::vector<std::string> PollNativeHelp() {
    std::vector<std::string> failures;
    auto& children=launchers.children;
    for(auto it=children.begin();it!=children.end();) {
        int status=0;const auto result=waitpid(*it,&status,WNOHANG);
        if(result==0||(result<0&&errno==EINTR)) {++it;continue;}
        if(result>0&&(!WIFEXITED(status)||WEXITSTATUS(status)!=0))
            failures.push_back("The desktop could not open Orbiter Help. Check the default web browser.");
        else if(result<0&&errno!=ECHILD)failures.push_back(std::string("Cannot collect help launcher: ")+std::strerror(errno));
        it=children.erase(it);
    }
    return failures;
}
}
