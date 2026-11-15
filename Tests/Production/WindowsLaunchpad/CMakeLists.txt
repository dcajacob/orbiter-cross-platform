cmake_minimum_required(VERSION 3.24)
project(WindowsLaunchpadCheck LANGUAGES CXX)
if(NOT WIN32 OR NOT MSVC)
    message(FATAL_ERROR "The Windows Launchpad check requires the matching MSVC SDK")
endif()
add_subdirectory("${ORBITER_SOURCE_ROOT}/Utils/Launchpad" launchpad)
target_sources(orbiter-launchpad PRIVATE LaunchpadProbe.cpp)
find_package(Qt6 6.4 REQUIRED COMPONENTS Widgets)
target_link_libraries(orbiter-launchpad PRIVATE Qt6::Widgets)

add_library(LaunchpadFlightProbe SHARED FlightProbe.cpp)
target_compile_features(LaunchpadFlightProbe PRIVATE cxx_std_17)
target_include_directories(LaunchpadFlightProbe PRIVATE
    "${ORBITER_TEST_RUNTIME}/Orbitersdk/include" "${ORBITER_SOURCE_ROOT}/Tests/Production")
target_link_libraries(LaunchpadFlightProbe PRIVATE
    "${ORBITER_TEST_RUNTIME}/Orbitersdk/lib/Orbiter.lib"
    "${ORBITER_TEST_RUNTIME}/Orbitersdk/lib/Orbitersdk.lib")
set_target_properties(LaunchpadFlightProbe PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${ORBITER_TEST_RUNTIME}/Modules/Plugin")
