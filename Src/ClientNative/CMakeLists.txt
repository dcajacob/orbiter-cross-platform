include(FetchContent)
if(POLICY CMP0135)
    cmake_policy(SET CMP0135 NEW)
endif()
set(GLFW_BUILD_EXAMPLES OFF CACHE BOOL "" FORCE)
set(GLFW_BUILD_TESTS OFF CACHE BOOL "" FORCE)
set(GLFW_BUILD_DOCS OFF CACHE BOOL "" FORCE)
set(GLFW_INSTALL OFF CACHE BOOL "" FORCE)
set(GLFW_LIBRARY_TYPE STATIC CACHE STRING "" FORCE)
FetchContent_Declare(glfw
    URL https://codeload.github.com/glfw/glfw/tar.gz/refs/tags/3.5.1
    URL_HASH SHA256=5234f4f29473e9a06bc7847d8371858dd135d38466eeeaa652fdc9f8f9ff0c20)
FetchContent_MakeAvailable(glfw)

add_executable(orbiter-native main.cpp Renderer.cpp)
target_link_libraries(orbiter-native PRIVATE orbiter_client_state glfw)
target_compile_definitions(orbiter-native PRIVATE GLFW_INCLUDE_NONE)
install(TARGETS orbiter-native RUNTIME DESTINATION bin)

install(FILES "${glfw_SOURCE_DIR}/LICENSE.md" DESTINATION share/licenses/orbiter-native RENAME GLFW.txt)
