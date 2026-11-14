cmake_minimum_required(VERSION 3.19)
project(OrbiterLaunchpad LANGUAGES CXX)

find_package(Qt6 6.4 REQUIRED COMPONENTS Widgets)

qt_add_executable(orbiter-launchpad WIN32 MACOSX_BUNDLE
    main.cpp
    Launchpad.cpp
    ScenarioEditor.cpp
    SimulatorProfile.cpp)
target_compile_features(orbiter-launchpad PRIVATE cxx_std_17)
target_link_libraries(orbiter-launchpad PRIVATE Qt6::Widgets)
set_target_properties(orbiter-launchpad PROPERTIES MACOSX_BUNDLE_BUNDLE_NAME "Orbiter Launchpad")

install(TARGETS orbiter-launchpad BUNDLE DESTINATION . RUNTIME DESTINATION bin)
