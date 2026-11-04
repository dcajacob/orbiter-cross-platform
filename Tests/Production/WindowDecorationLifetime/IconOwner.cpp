// Licensed under the MIT License
// Real decorated Wayland title updates, with an independent lost-object control.
#define GLFW_INCLUDE_NONE
#include <GLFW/glfw3.h>
#include <pthread.h>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <string>
#include <thread>

static void* lose(void*) {
    void* value=std::malloc(73);if(!value)std::abort();
    std::memset(value,23,73);__asm__ __volatile__("" : : "g"(value) : "memory");return nullptr;
}
int main(int argc,char** argv) {
    if(argc!=2 || (std::string(argv[1])!="normal" && std::string(argv[1])!="lost"))return 2;
    glfwSetErrorCallback([](int code,const char* message){std::fprintf(stderr,"GLFW %d: %s\n",code,message);});
    glfwInitHint(GLFW_PLATFORM,GLFW_PLATFORM_WAYLAND);
    glfwInitHint(GLFW_WAYLAND_LIBDECOR,GLFW_WAYLAND_PREFER_LIBDECOR);
    if(!glfwInit())return 3;
    auto* window=glfwCreateWindow(320,180,"Icon ownership 0",nullptr,nullptr);
    if(!window){glfwTerminate();return 4;}
    glfwMakeContextCurrent(window);
    auto clear=reinterpret_cast<void(*)(unsigned)>(glfwGetProcAddress("glClear"));
    if(!clear){glfwDestroyWindow(window);glfwTerminate();return 5;}
    for(unsigned frame=0;frame<120;++frame) {
        const std::string title="Icon ownership "+std::to_string(frame);
        glfwSetWindowTitle(window,title.c_str());
        glfwPollEvents();clear(0x00004000);glfwSwapBuffers(window);
        std::this_thread::sleep_for(std::chrono::milliseconds(10));
    }
    {std::ifstream maps("/proc/self/maps");std::ofstream loaded("icon-loaded-modules.txt");loaded<<maps.rdbuf();}
    glfwDestroyWindow(window);glfwTerminate();
    if(std::string(argv[1])=="lost") {
        pthread_t thread;if(pthread_create(&thread,nullptr,lose,nullptr) || pthread_join(thread,nullptr))return 6;
    }
    std::printf("Completed 120 real swaps/title updates and window teardown; mode=%s\n",argv[1]);
    std::fflush(stdout);return 0;
}
