cmake_minimum_required(VERSION 3.24)
project(OrbiterWindowsInstallProbe LANGUAGES CXX)
add_library(LaunchpadFlightProbe SHARED FlightProbe.cpp)
target_compile_features(LaunchpadFlightProbe PRIVATE cxx_std_17)
target_include_directories(LaunchpadFlightProbe PRIVATE
    "${ORBITER_TEST_RUNTIME}/Orbitersdk/include" "${CMAKE_CURRENT_SOURCE_DIR}/..")
target_link_libraries(LaunchpadFlightProbe PRIVATE
    "${ORBITER_TEST_RUNTIME}/Orbitersdk/lib/Orbiter.lib"
    "${ORBITER_TEST_RUNTIME}/Orbitersdk/lib/Orbitersdk.lib")

add_executable(ResolveSdkFlightProfile ResolveSdkFlightProfile.cpp
    ../../../Utils/InstalledProfile/WindowsProfile.cpp)
target_compile_features(ResolveSdkFlightProfile PRIVATE cxx_std_17)
