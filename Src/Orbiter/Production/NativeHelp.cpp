// Licensed under the MIT License
#include "NativeHelp.h"
#include <cerrno>
#include <cstring>
#include <cstdlib>
#include <cstdint>
#include <fcntl.h>
#include <fstream>
#include <iostream>
#include <spawn.h>
#include <stdexcept>
#include <sys/stat.h>
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
struct Descriptor {
    int value;
    explicit Descriptor(int fd):value(fd) {if(fd<0)throw std::runtime_error(std::strerror(errno));}
    ~Descriptor() {close(value);}
};
std::string LaunchPage(const std::string& url) {
    // Older xdg-open versions convert file URLs to paths, discarding the query.
    // An immutable local page carries the whole URL through either convention.
    // Keep it in the user's cache: browsers can read it after this process exits.
    const char* cache=std::getenv("XDG_CACHE_HOME");
    std::filesystem::path root;
    if(cache&&*cache&&std::filesystem::path(cache).is_absolute())root=cache;
    else {
        const char* home=std::getenv("HOME");
        if(!home||!*home||!std::filesystem::path(home).is_absolute())
            throw std::runtime_error("Cannot locate the user cache for desktop help");
        root=std::filesystem::path(home)/".cache";
    }
    root/= "orbiter/help-launch";
    std::filesystem::create_directories(root);
    Descriptor directory(open(root.c_str(),O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC));
    struct stat info{};
    if(fstat(directory.value,&info)||info.st_uid!=getuid()||fchmod(directory.value,0700))
        throw std::runtime_error("Desktop help cache is not owned by this user");
    // Encode every URL delimiter inside the script, including '<', quotes and
    // ampersands. No URL text can become HTML or JavaScript source.
    const std::string page="<!doctype html><meta charset=\"utf-8\"><title>Orbiter Help</title>\n"
        "<script>location.replace(decodeURIComponent(\""+Encode(url)+"\"));</script>\n";
    // This is a cache key, not a trust check. Existing content must match exactly;
    // collisions, non-regular files and links are never replaced or followed.
    std::uint64_t key=14695981039346656037ull;
    for(unsigned char byte:page) {key^=byte;key*=1099511628211ull;}
    const auto name=std::to_string(key)+".html";
    auto matches=[&] {
        Descriptor file(openat(directory.value,name.c_str(),O_RDONLY|O_NOFOLLOW|O_CLOEXEC));
        struct stat existing{};
        if(fstat(file.value,&existing)||!S_ISREG(existing.st_mode)||existing.st_uid!=getuid()||
                existing.st_size!=static_cast<off_t>(page.size()))return false;
        std::string actual(page.size(),'\0');size_t offset=0;
        while(offset<actual.size()) {
            const auto count=read(file.value,actual.data()+offset,actual.size()-offset);
            if(count<0&&errno==EINTR)continue;
            if(count<=0)return false;
            offset+=count;
        }
        return actual==page;
    };
    std::string temporary=(root/".launch-XXXXXX").string();
    Descriptor file(mkstemp(temporary.data()));
    try {
        size_t offset=0;
        while(offset<page.size()) {
            const auto count=write(file.value,page.data()+offset,page.size()-offset);
            if(count<0&&errno==EINTR)continue;
            if(count<=0)throw std::runtime_error("Cannot write desktop help launch page");
            offset+=count;
        }
        if(linkat(AT_FDCWD,temporary.c_str(),directory.value,name.c_str(),0)!=0) {
            if(errno!=EEXIST||!matches())throw std::runtime_error("Desktop help launch cache conflict");
        }
    }catch(...) {unlink(temporary.c_str());throw;}
    unlink(temporary.c_str());
    return "file://"+Encode((root/name).generic_string(),true);
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
    const auto launch=LaunchPage(url);
    char command[]="xdg-open";
    char* args[]={command,const_cast<char*>(launch.c_str()),nullptr};
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
