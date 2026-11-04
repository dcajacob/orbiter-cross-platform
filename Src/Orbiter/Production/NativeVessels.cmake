# Actual production vessel source and source-built stock module, initially a
# headless host. Native cockpit/input/particle capability gaps fail explicitly.
if(WIN32)
    message(FATAL_ERROR "Native vessel host currently requires Linux; Windows retains the original application adapters")
endif()
add_library(orbiter_production_vessels SHARED
    NativeVesselObservation.cpp
    FlightControls.cpp ../Keymap.cpp NativeRenderApi.cpp NativeParticle.cpp ../CelSphereAPI.cpp ../DrawAPI.cpp ../Camera.cpp ../CameraControl.cpp NativeCameraProjection.cpp ../Vessel.cpp ../VesselSdk.cpp ../Vesselstatus.cpp ../SuperVessel.cpp
    ../VesselLights.cpp ../LightEmitter.cpp ../VesselFlightMath.cpp ../FlightSdk.cpp ../ScenarioSdk.cpp ../VesselRecorder.cpp ../CollisionCore.cpp
    NativeCockpitUnavailable.cpp NativeVesselApplication.cpp NativeVesselModule.cpp NativeWorldVesselServices.cpp)
target_link_libraries(orbiter_production_vessels PUBLIC orbiter_production_boundary)
target_compile_features(orbiter_production_vessels PUBLIC cxx_std_17)
target_compile_definitions(orbiter_production_vessels PRIVATE ORBITER_PRODUCTION_OBSERVATION)
target_include_directories(orbiter_production_vessels PRIVATE "${CMAKE_CURRENT_LIST_DIR}/NativeObservation")
target_link_options(orbiter_production_vessels PRIVATE -Wl,--no-undefined)
if(ORBITER_BUILD_NATIVE_COCKPIT)
    include(NativeCockpit.cmake)
endif()
add_library(native_shuttlepb MODULE ../../../Src/Vessel/ShuttlePB/ShuttlePB.cpp)
target_compile_definitions(native_shuttlepb PRIVATE ORBITER_NATIVE_MODULE)
target_link_libraries(native_shuttlepb PRIVATE orbiter_production_vessels)
set_target_properties(native_shuttlepb PROPERTIES PREFIX "" OUTPUT_NAME ShuttlePB
    LIBRARY_OUTPUT_DIRECTORY "${PROJECT_BINARY_DIR}/NativeModules/Vessel")
add_executable(production_native_vessel_observer ../../../Tests/Production/Vessels/NativeObserve.cpp)
target_link_libraries(production_native_vessel_observer PRIVATE orbiter_production_vessels)
add_dependencies(production_native_vessel_observer native_shuttlepb)

add_executable(orbiter-production NativeApplication.cpp)
target_link_libraries(orbiter-production PRIVATE orbiter_production_vessels)
add_dependencies(orbiter-production native_shuttlepb)

option(ORBITER_BUILD_ATLANTIS_DIAGNOSTIC "Build isolated unqualified Atlantis simulation test host" OFF)
if(ORBITER_BUILD_ATLANTIS_DIAGNOSTIC)
    if(NOT ORBITER_BUILD_NATIVE_COCKPIT)
        message(FATAL_ERROR "The real Atlantis diagnostic needs the native cockpit and stock modules")
    endif()
    add_executable(production_atlantis_diagnostic NativeApplication.cpp)
    target_compile_definitions(production_atlantis_diagnostic PRIVATE ORBITER_ATLANTIS_DIAGNOSTIC)
    target_link_libraries(production_atlantis_diagnostic PRIVATE orbiter_production_vessels)
    add_dependencies(production_atlantis_diagnostic native_deltaglider native_atlantis native_atlantis_tank native_atlantis_srb)
endif()
