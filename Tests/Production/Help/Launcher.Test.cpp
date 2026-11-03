// Licensed under the MIT License
#include "Production/NativeHelp.h"
#include <cerrno>
#include <cstdlib>
#include <fcntl.h>
#include <fstream>
#include <iostream>
#include <sys/wait.h>
#include <thread>
#include <unistd.h>
using namespace orbiter::production;
void require(bool ok,const char* message) {if(!ok)throw std::runtime_error(message);}
std::string decodePath(const std::string& url) {
    require(url.rfind("file:///",0)==0,"Desktop transport is not a local file URL");
    std::string result;
    for(size_t i=7;i<url.size();++i) {
        if(url[i]=='%') {
            require(i+2<url.size(),"Incomplete transport escape");
            result+=char(std::stoi(url.substr(i+1,2),nullptr,16));i+=2;
        }else result+=url[i];
    }
    return result;
}
std::string contents(const std::filesystem::path& file) {
    std::ifstream stream(file);return {(std::istreambuf_iterator<char>(stream)),{}};
}
int main(int argc,char** argv) {
    try {
        if(argc==2&&std::string(argv[1]).find("file://")==0) {
            require(!std::getenv("LD_PRELOAD")&&!std::getenv("LD_LIBRARY_PATH"),"Engine loader environment reached desktop launcher");
            errno=0;
            require(fcntl(std::atoi(std::getenv("ORBITER_HELP_TEST_FD")),F_GETFD)==-1&&errno==EBADF,"Engine descriptor reached desktop launcher");
            std::ofstream(std::getenv("ORBITER_HELP_TEST_OUTPUT"))<<argv[1];
            require(contents(decodePath(argv[1])).find("location.replace(decodeURIComponent(")!=std::string::npos,"Desktop launch page is not readable");
            return std::getenv("ORBITER_HELP_TEST_FAIL")?3:0;
        }
        require(argc==2,"Expected new test directory");
        const auto directory=std::filesystem::absolute(argv[1]);
        require(std::filesystem::create_directory(directory),"Test output already exists");
        setenv("XDG_CACHE_HOME",(directory/"cache with spaces").c_str(),1);
        std::filesystem::copy_file(std::filesystem::canonical("/proc/self/exe"),directory/"xdg-open");
        setenv("PATH",directory.c_str(),1);
        setenv("LD_PRELOAD","/nonexistent/orbiter-probe.so",1);
        setenv("LD_LIBRARY_PATH","/nonexistent/orbiter-modules",1);
        const int fd=open((directory/"owned-stream").c_str(),O_CREAT|O_WRONLY,0600);
        require(fd>=3,"Cannot create inherited descriptor fixture");
        setenv("ORBITER_HELP_TEST_FD",std::to_string(fd).c_str(),1);
        const std::string url="file:///original help/topic.htm?topic=one%20two&literal=$(no-shell)";
        std::string transport;
        for(bool fail:{false,true}) {
            const auto output=directory/(fail?"failed.txt":"success.txt");
            setenv("ORBITER_HELP_TEST_OUTPUT",output.c_str(),1);
            if(fail)setenv("ORBITER_HELP_TEST_FAIL","1",1);
            OpenNativeHelp(url);
            std::vector<std::string> errors;bool reaped=false;
            for(int i=0;i<500&&!reaped;++i) {
                auto events=PollNativeHelp();errors.insert(errors.end(),events.begin(),events.end());
                // Observe without reaping: a child may exit immediately after
                // PollNativeHelp(), and the service must collect it next time.
                std::ifstream children("/proc/self/task/"+std::to_string(getpid())+"/children");
                std::string child;children>>child;reaped=child.empty();
                if(!reaped)std::this_thread::sleep_for(std::chrono::milliseconds(10));
            }
            require(reaped,"Help launcher was not reaped");
            require(errors.size()==(fail?1u:0u),"Launcher failure not reported exactly once");
            std::ifstream file(output);std::string actual((std::istreambuf_iterator<char>(file)),{});
            require(actual.find('?')==std::string::npos&&actual.find('%')!=std::string::npos,"Desktop transport still depends on query preservation or unescaped paths");
            const auto page=contents(decodePath(actual));
            require(page.find("file%3A%2F%2F%2Foriginal%20help%2Ftopic.htm%3Ftopic%3Done%2520two%26literal%3D%24%28no-shell%29")!=std::string::npos,
                "Original URL changed inside the launch page");
            if(!transport.empty())require(actual==transport,"Identical help requests did not reuse an immutable page");
            transport=actual;
        }
        close(fd);
        const auto cached=decodePath(transport), original=contents(cached);
        const auto escaped=url+"&unsafe=</script>\"\\\n";
        OpenNativeHelp(escaped);
        bool escapedReaped=false;size_t escapedErrors=0;
        for(int i=0;i<500&&!escapedReaped;++i) {
            escapedErrors+=PollNativeHelp().size();
            std::ifstream children("/proc/self/task/"+std::to_string(getpid())+"/children");
            std::string child;children>>child;escapedReaped=child.empty();
            if(!escapedReaped)std::this_thread::sleep_for(std::chrono::milliseconds(10));
        }
        require(escapedReaped&&escapedErrors==1,"Escaped request child was not collected exactly once");
        const auto escapedPage=contents(decodePath(contents(directory/"failed.txt")));
        require(escapedPage.find("%3C%2Fscript%3E%22%5C%0A")!=std::string::npos&&
                escapedPage.find("unsafe=</script>")==std::string::npos,"URL escaped its script string");
        require(contents(cached)==original,"A different request overwrote a browser's launch page");
        // A pre-existing link must neither be followed nor replaced.
        std::filesystem::remove(cached);
        const auto sentinel=directory/"sentinel";
        std::ofstream(sentinel)<<"untouched";
        std::filesystem::create_symlink(sentinel,cached);
        bool conflict=false;try{OpenNativeHelp(url);}catch(const std::exception&){conflict=true;}
        require(conflict&&contents(sentinel)=="untouched","Cache link followed or replaced");
        std::filesystem::remove(cached);
        std::filesystem::remove(directory/"xdg-open");
        bool missing=false;try{OpenNativeHelp(url);}catch(const std::exception&){missing=true;}
        require(missing,"Missing desktop launcher accepted");
        std::cout<<"Immutable desktop launch pages, URL preservation, cache links, environment, descriptor isolation, failures and child reaping passed\n";
    }catch(const std::exception& error){std::cerr<<error.what()<<'\n';return 1;}
}
