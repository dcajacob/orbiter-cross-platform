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
int main(int argc,char** argv) {
    try {
        if(argc==2&&std::string(argv[1]).find("file://")==0) {
            require(!std::getenv("LD_PRELOAD")&&!std::getenv("LD_LIBRARY_PATH"),"Engine loader environment reached desktop launcher");
            errno=0;
            require(fcntl(std::atoi(std::getenv("ORBITER_HELP_TEST_FD")),F_GETFD)==-1&&errno==EBADF,"Engine descriptor reached desktop launcher");
            std::ofstream(std::getenv("ORBITER_HELP_TEST_OUTPUT"))<<argv[1];
            return std::getenv("ORBITER_HELP_TEST_FAIL")?3:0;
        }
        require(argc==2,"Expected new test directory");
        const auto directory=std::filesystem::absolute(argv[1]);
        require(std::filesystem::create_directory(directory),"Test output already exists");
        std::filesystem::copy_file(std::filesystem::canonical("/proc/self/exe"),directory/"xdg-open");
        setenv("PATH",directory.c_str(),1);
        setenv("LD_PRELOAD","/nonexistent/orbiter-probe.so",1);
        setenv("LD_LIBRARY_PATH","/nonexistent/orbiter-modules",1);
        const int fd=open((directory/"owned-stream").c_str(),O_CREAT|O_WRONLY,0600);
        require(fd>=3,"Cannot create inherited descriptor fixture");
        setenv("ORBITER_HELP_TEST_FD",std::to_string(fd).c_str(),1);
        const std::string url="file:///original help/topic.htm?topic=one%20two&literal=$(no-shell)";
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
            require(actual==url,"Help URL was interpreted or split");
        }
        close(fd);
        std::filesystem::remove(directory/"xdg-open");
        bool missing=false;try{OpenNativeHelp(url);}catch(const std::exception&){missing=true;}
        require(missing,"Missing desktop launcher accepted");
        std::cout<<"Desktop launch arguments, environment, descriptor isolation, failures and child reaping passed\n";
    }catch(const std::exception& error){std::cerr<<error.what()<<'\n';return 1;}
}
