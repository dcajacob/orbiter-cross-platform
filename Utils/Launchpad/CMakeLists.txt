cmake_minimum_required(VERSION 3.19)
project(OrbiterLaunchpad LANGUAGES CXX)

find_package(Qt6 6.4 REQUIRED COMPONENTS Widgets)

add_library(orbiter-launchpad-ui STATIC
    ../ProjectLauncher/RuntimeLibrary.cpp
    AboutDialog.cpp
    Launchpad.cpp
    ExtraPage.cpp
    FlightSettings.cpp
    ModulesPage.cpp
    ScenarioEditor.cpp
    SimulatorProfile.cpp)
include("${CMAKE_CURRENT_LIST_DIR}/../../cmake/OrbiterAbout.cmake")
orbiter_configure_about()
target_include_directories(orbiter-launchpad-ui PRIVATE "${CMAKE_CURRENT_BINARY_DIR}")
if(WIN32)
    target_sources(orbiter-launchpad-ui PRIVATE ../InstalledProfile/WindowsProfile.cpp)
endif()
target_compile_features(orbiter-launchpad-ui PUBLIC cxx_std_17)
target_link_libraries(orbiter-launchpad-ui PUBLIC Qt6::Widgets)

if(CMAKE_SYSTEM_NAME STREQUAL "Linux")
    if(POLICY CMP0135)
        cmake_policy(SET CMP0135 NEW)
    endif()
    include(FetchContent)
    enable_language(C)
    set(ORBITER_GLFW_ARCHIVE "https://codeload.github.com/glfw/glfw/tar.gz/refs/tags/3.5.1"
        CACHE STRING "Source archive for the GLFW version used by the native simulator")
    set(GLFW_BUILD_EXAMPLES OFF CACHE BOOL "Build GLFW examples" FORCE)
    set(GLFW_BUILD_TESTS OFF CACHE BOOL "Build GLFW tests" FORCE)
    set(GLFW_BUILD_DOCS OFF CACHE BOOL "Build GLFW documentation" FORCE)
    set(GLFW_INSTALL OFF CACHE BOOL "Install GLFW with Launchpad" FORCE)
    set(GLFW_LIBRARY_TYPE STATIC CACHE STRING "Launchpad GLFW linkage" FORCE)
    FetchContent_Declare(glfw URL "${ORBITER_GLFW_ARCHIVE}"
        URL_HASH SHA256=5234f4f29473e9a06bc7847d8371858dd135d38466eeeaa652fdc9f8f9ff0c20)
    FetchContent_MakeAvailable(glfw)
    target_sources(orbiter-launchpad-ui PRIVATE JoystickSetup.cpp JoystickShortcutDialog.cpp
        ../../Src/Orbiter/Keymap.cpp ../../Src/Orbiter/ConfigFile.cpp)
    target_include_directories(orbiter-launchpad-ui PRIVATE
        ../../OVP/OGLClient/Native ../../Src/Orbiter ../../Orbitersdk/include)
    target_compile_definitions(orbiter-launchpad-ui PRIVATE GLFW_INCLUDE_NONE)
    target_link_libraries(orbiter-launchpad-ui PRIVATE glfw)
    qt_add_resources(orbiter-launchpad-ui "launchpad_installer" PREFIX "/launchpad/install"
        BASE "${CMAKE_CURRENT_SOURCE_DIR}/../StockDataInstaller" FILES ../StockDataInstaller/launch_linux.py)
endif()

set(orbiter_bitmaps "${CMAKE_CURRENT_SOURCE_DIR}/../../Src/Orbiter/Bitmaps")
qt_add_resources(orbiter-launchpad-ui "launchpad_banner" PREFIX "/launchpad" BASE "${orbiter_bitmaps}"
    FILES "${orbiter_bitmaps}/banner.bmp" "${orbiter_bitmaps}/Icon64.bmp")

get_filename_component(orbiter_source "${CMAKE_CURRENT_SOURCE_DIR}/../.." ABSOLUTE)
qt_add_resources(orbiter-launchpad-ui "launchpad_about" PREFIX "/launchpad/about" BASE "${orbiter_source}"
    FILES "${orbiter_source}/Html/Main/Credit/credit.htm" "${orbiter_source}/Src/Orbiter/Disclaimer.txt")

set(scenario_help "${CMAKE_CURRENT_SOURCE_DIR}/../../Html/Scenarios")
file(GLOB_RECURSE scenario_art CONFIGURE_DEPENDS
    "${scenario_help}/*.htm" "${scenario_help}/*.jpg" "${scenario_help}/*.gif" "${scenario_help}/*.png")
qt_add_resources(orbiter-launchpad-ui "launchpad_scenario_help" PREFIX "/launchpad/scenarios"
    BASE "${scenario_help}" FILES ${scenario_art})

qt_add_executable(orbiter-launchpad WIN32 MACOSX_BUNDLE main.cpp)
target_link_libraries(orbiter-launchpad PRIVATE orbiter-launchpad-ui)
set_target_properties(orbiter-launchpad PROPERTIES MACOSX_BUNDLE_BUNDLE_NAME "Orbiter Launchpad")

install(TARGETS orbiter-launchpad BUNDLE DESTINATION . RUNTIME DESTINATION bin)
