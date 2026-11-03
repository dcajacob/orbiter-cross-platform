// Licensed under the MIT License
// Actual pinned GLFW Wayland window; no Orbiter, font renderer or mipmap work.
#define GLFW_INCLUDE_NONE
#include <GLFW/glfw3.h>
#include <chrono>
#include <cstdio>
#include <fstream>
#include <string>
#include <thread>

int main(int argc,char** argv) {
    if(argc!=2 || (std::string(argv[1])!="prefer" && std::string(argv[1])!="disable"))return 2;
    glfwSetErrorCallback([](int code,const char* text){std::fprintf(stderr,"GLFW %d: %s\n",code,text);});
    glfwInitHint(GLFW_PLATFORM,GLFW_PLATFORM_WAYLAND);
    glfwInitHint(GLFW_WAYLAND_LIBDECOR,std::string(argv[1])=="prefer" ?
        GLFW_WAYLAND_PREFER_LIBDECOR : GLFW_WAYLAND_DISABLE_LIBDECOR);
    if(!glfwInit())return 3;
    auto window=glfwCreateWindow(320,180,"Wayland decoration lifetime",nullptr,nullptr);
    if(!window){glfwTerminate();return 4;}
    glfwMakeContextCurrent(window);
    auto clear=reinterpret_cast<void(*)(unsigned)>(glfwGetProcAddress("glClear"));
    if(!clear){glfwDestroyWindow(window);glfwTerminate();return 5;}
    for(unsigned frame=0;frame<120;++frame) {
        glfwPollEvents();clear(0x00004000);glfwSwapBuffers(window);
        std::this_thread::sleep_for(std::chrono::milliseconds(10));
    }
    {
        std::ifstream maps("/proc/self/maps");
        std::ofstream output(std::string("loaded-")+argv[1]+".txt");
        output<<maps.rdbuf();
    }
    glfwDestroyWindow(window);glfwTerminate();
    std::printf("GLFW %s: %s decorations, 120 swaps, window/context terminated\n",glfwGetVersionString(),argv[1]);
    std::fflush(stdout);
}
