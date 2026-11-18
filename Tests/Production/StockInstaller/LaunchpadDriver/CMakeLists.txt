cmake_minimum_required(VERSION 3.24)
project(InstalledLaunchpadDriver LANGUAGES CXX)
find_package(Qt6 6.4 REQUIRED COMPONENTS Widgets)
add_library(launchpad-driver SHARED ../../MacPhase7/Desktop/LaunchpadProbe.cpp)
target_link_libraries(launchpad-driver PRIVATE Qt6::Widgets)
set_target_properties(launchpad-driver PROPERTIES PREFIX "" SKIP_BUILD_RPATH TRUE)
if(APPLE)
    # dyld loads this test driver before the application. Resolve Qt from the installed app.
    set_target_properties(launchpad-driver PROPERTIES
        BUILD_WITH_INSTALL_RPATH TRUE INSTALL_RPATH "@executable_path/../Frameworks")
endif()
