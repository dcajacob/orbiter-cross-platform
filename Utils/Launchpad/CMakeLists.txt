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

set(orbiter_bitmaps "${CMAKE_CURRENT_SOURCE_DIR}/../../Src/Orbiter/Bitmaps")
qt_add_resources(orbiter-launchpad "launchpad_banner" PREFIX "/launchpad" BASE "${orbiter_bitmaps}"
    FILES "${orbiter_bitmaps}/banner.bmp")

set(scenario_help "${CMAKE_CURRENT_SOURCE_DIR}/../../Html/Scenarios")
file(GLOB_RECURSE scenario_art CONFIGURE_DEPENDS
    "${scenario_help}/*.htm" "${scenario_help}/*.jpg" "${scenario_help}/*.gif" "${scenario_help}/*.png")
qt_add_resources(orbiter-launchpad "launchpad_scenario_help" PREFIX "/launchpad/scenarios"
    BASE "${scenario_help}" FILES ${scenario_art})

install(TARGETS orbiter-launchpad BUNDLE DESTINATION . RUNTIME DESTINATION bin)
