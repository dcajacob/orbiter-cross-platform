// Licensed under the MIT License
// A second owned Wayland client for real compositor keyboard-focus transfers.
#define GLFW_INCLUDE_NONE
#include <GLFW/glfw3.h>
#include <stdio.h>

static void error(int code,const char* message) {
    fprintf(stderr,"GLFW %d: %s\n",code,message);
}
int main(void) {
    glfwSetErrorCallback(error);
    glfwInitHint(GLFW_PLATFORM,GLFW_PLATFORM_WAYLAND);
    if(!glfwInit())return 1;
    glfwWindowHint(GLFW_DECORATED,GLFW_FALSE);
    GLFWwindow* window=glfwCreateWindow(96,64,"Orbiter owned focus sink",NULL,NULL);
    if(!window){glfwTerminate();return 2;}
    glfwMakeContextCurrent(window);
    glfwSwapBuffers(window);
    while(!glfwWindowShouldClose(window))glfwWaitEvents();
    glfwDestroyWindow(window);glfwTerminate();return 0;
}
