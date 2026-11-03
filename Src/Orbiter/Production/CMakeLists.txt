# Internal shared production boundary. This is not yet the complete engine.
if(CMAKE_SOURCE_DIR STREQUAL CMAKE_CURRENT_SOURCE_DIR)
    cmake_minimum_required(VERSION 3.19)
    project(OrbiterProductionBoundary LANGUAGES CXX)
    include(CTest)
endif()
option(ORBITER_BUILD_NATIVE_CELESTIAL_MODULES "Build source-rebuilt production celestial modules" OFF)
option(ORBITER_BUILD_NATIVE_VESSELS "Build the production native vessel headless host" OFF)
option(ORBITER_BUILD_NATIVE_COCKPIT "Build the native cockpit integration candidate" OFF)
if(CMAKE_SYSTEM_NAME STREQUAL "Linux" AND ORBITER_BUILD_NATIVE_VESSELS)
    add_subdirectory(Math)
endif()
if(ORBITER_BUILD_NATIVE_COCKPIT AND NOT ORBITER_BUILD_NATIVE_VESSELS)
    message(FATAL_ERROR "Native cockpit integration requires production native vessels")
endif()
# Use the original application's pinned zlib when it is already configured.
# Standalone Windows builds use that same source; Linux uses its native zlib.
if(TARGET zlibstatic)
    set(_archive_zlib zlibstatic)
    get_target_property(_archive_zlib_source zlibstatic SOURCE_DIR)
    get_target_property(_archive_zlib_build zlibstatic BINARY_DIR)
    set(_archive_zlib_includes "${_archive_zlib_source}" "${_archive_zlib_build}")
elseif(WIN32)
    enable_language(C)
    include(FetchContent)
    set(CMAKE_POLICY_VERSION_MINIMUM 3.5)
    set(SKIP_INSTALL_ALL ON)
    FetchContent_Declare(zlib GIT_REPOSITORY https://github.com/madler/zlib.git
        GIT_TAG cacf7f1d4e3d44d871b605da3b647f07d718623f)
    FetchContent_MakeAvailable(zlib)
    set(_archive_zlib zlibstatic)
    set(_archive_zlib_includes "${zlib_SOURCE_DIR}" "${zlib_BINARY_DIR}")
else()
    find_package(ZLIB 1.2.11 REQUIRED)
    set(_archive_zlib ZLIB::ZLIB)
endif()
add_library(orbiter_production_boundary SHARED
    Random.cpp CameraServices.cpp VesselCoreSupport.cpp VesselServices.cpp WorldVesselServices.cpp SurfaceNavigation.cpp SurfaceServices.cpp SurfaceNames.cpp Session.cpp WorldOwner.cpp NativeModule.cpp NativeCelestialApi.cpp NativeCelestialServices.cpp NavigationServices.cpp ElevationServices.cpp NativeElevationServices.cpp ResourceResolver.cpp MeshData.cpp MeshServices.cpp BodyServices.cpp RigidBodyServices.cpp CelestialServices.cpp ScenarioColor.cpp
    ../MfdOrbitGeometry.cpp ../Body.cpp ../Rigidbody.cpp ../BodyIntegrator.cpp ../Element.cpp
    ../Vecmat.cpp ../TimeData.cpp ../Config.cpp ../ConfigFile.cpp ../Mesh.cpp ../State.cpp
    ../Psys.cpp ../Vesselbase.cpp ../Planet.cpp ../Base.cpp ../Baseobj.cpp ../Shadow.cpp ../elevmgr.cpp ../elevmgrFile.cpp ../Nav.cpp ../PsysGravity.cpp ../PinesGrav.cpp ../PinesGravFile.cpp ../Celbody.cpp ../CelbodyFile.cpp ../ElementFile.cpp ../Star.cpp ../ZTreeMgr.cpp)
target_compile_features(orbiter_production_boundary PUBLIC cxx_std_17)
target_compile_definitions(orbiter_production_boundary
    PUBLIC ORBITER_PRODUCTION_SHARED ORBITER_NATIVE_BUILD_CONFIGURATION="$<CONFIG>" PRIVATE ORBITER_PRODUCTION_BUILD)
target_include_directories(orbiter_production_boundary PUBLIC "${CMAKE_CURRENT_SOURCE_DIR}/.."
    "${CMAKE_CURRENT_SOURCE_DIR}/../../../Orbitersdk/include")
set_target_properties(orbiter_production_boundary PROPERTIES
    CXX_EXTENSIONS OFF FOLDER Core WINDOWS_EXPORT_ALL_SYMBOLS ON)
target_link_libraries(orbiter_production_boundary PRIVATE ${CMAKE_DL_LIBS})
if(WIN32)
    target_compile_definitions(orbiter_production_boundary PRIVATE NOMINMAX)
    target_link_libraries(orbiter_production_boundary PRIVATE user32)
endif()
target_link_libraries(orbiter_production_boundary PRIVATE ${_archive_zlib})
if(TARGET orbiter_reference_math)
    target_link_libraries(orbiter_production_boundary PUBLIC orbiter_reference_math)
    target_compile_definitions(orbiter_production_boundary PRIVATE ORBITER_REFERENCE_MATH)
endif()
target_include_directories(orbiter_production_boundary PRIVATE ${_archive_zlib_includes})

# The native bootstrap is tied to this SDK build, source ABI and toolchain.
# Consumers use its generated header and linked target; independently configured
# engine builds deliberately get different tokens, even from identical sources.
if(NOT DEFINED ORBITER_NATIVE_BUILD_TOKEN)
    string(RANDOM LENGTH 32 ALPHABET 0123456789abcdef ORBITER_NATIVE_BUILD_TOKEN)
    set(ORBITER_NATIVE_BUILD_TOKEN "${ORBITER_NATIVE_BUILD_TOKEN}" CACHE INTERNAL "Native engine/SDK build token")
endif()
get_target_property(_native_sources orbiter_production_boundary SOURCES)
file(GLOB _native_headers CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/*.h" "${CMAKE_CURRENT_SOURCE_DIR}/../*.h"
    "${CMAKE_CURRENT_SOURCE_DIR}/../../../Orbitersdk/include/*.h")
list(APPEND _native_sources ${_native_headers} "${CMAKE_CURRENT_LIST_FILE}" "${CMAKE_CURRENT_SOURCE_DIR}/NativeBuild.h.in"
    "${CMAKE_CURRENT_SOURCE_DIR}/../../../Orbitersdk/include/OrbiterMeshData.h")
if(ORBITER_BUILD_NATIVE_VESSELS)
    list(APPEND _native_sources
        ../Vessel.cpp ../VesselSdk.cpp ../Vesselstatus.cpp ../SuperVessel.cpp
        ../VesselLights.cpp ../LightEmitter.cpp ../VesselFlightMath.cpp ../FlightSdk.cpp ../ScenarioSdk.cpp ../VesselRecorder.cpp ../CollisionCore.cpp
        NativeCockpitUnavailable.cpp NativeVesselApplication.cpp NativeVesselModule.cpp NativeWorldVesselServices.cpp
        FlightControls.cpp ../Keymap.cpp NativeApplication.cpp NativeRenderApi.cpp NativeParticle.cpp NativeVesselObservation.cpp NativeObservation/ApplicationObservation.h ../CelSphereAPI.cpp ../DrawAPI.cpp ../Camera.cpp ../CameraControl.cpp NativeCameraProjection.cpp NativeVessels.cmake ../../Vessel/ShuttlePB/ShuttlePB.cpp ../../Vessel/ShuttlePB/NativeShuttlePBFactory.inc)
endif()
if(ORBITER_BUILD_NATIVE_COCKPIT)
    list(APPEND _native_sources
        NativeCockpit.cmake SystemPlayback.h PlaybackAnnotation.inc GuiMenuButton.inc GuiAnimatedControls.inc GuiOptionControls.inc NativeJoystick.h NativeAnnotations.cpp ScreenAnnotationMethods.inc NativeScript.cpp NativeInterpreterSdk.cpp ../CockpitSdk.cpp NativeCockpitMfd.cpp NativeCockpitProjection.cpp NativeCockpitGui.cpp ../MenuInfoBar.cpp ../DlgFocus.cpp ../DlgMenuCfg.cpp ../DlgTacc.cpp ../DlgCamera.cpp ../DlgInfo.cpp ../DlgMap.cpp ../DlgOptions.cpp NativeCockpitVessel.cpp
        CockpitVesselMethods.inc CockpitCameraMethods.inc CockpitPanelMethods.inc
        ../Pane.cpp ../hud.cpp ../Defpanel.cpp ../Panel2D.cpp ../VCockpit.cpp ../Select.cpp ../Astro.cpp
        ../Mfd.cpp ../MfdUser.cpp ../VectorMap.cpp ../MfdOrbit.cpp ../MfdSurface.cpp ../MfdMap.cpp ../MfdHsi.cpp
        ../MfdLanding.cpp ../MfdDocking.cpp ../MfdAlign.cpp ../MfdSync.cpp ../MfdTransfer.cpp ../MfdComms.cpp
        ../../../OVP/OGLClient/dependencies.lock.json)
endif()
list(APPEND _native_sources ${ORBITER_REFERENCE_MATH_INPUTS})
set(_native_input "${ORBITER_NATIVE_BUILD_TOKEN}|${CMAKE_CXX_COMPILER_ID}|${CMAKE_CXX_COMPILER_VERSION}|${CMAKE_SYSTEM_NAME}|${CMAKE_SYSTEM_PROCESSOR}|${CMAKE_SIZEOF_VOID_P}|${CMAKE_CXX_FLAGS}|${CMAKE_CXX_FLAGS_DEBUG}|${CMAKE_CXX_FLAGS_RELEASE}|${CMAKE_MSVC_RUNTIME_LIBRARY}|${CMAKE_C_COMPILER_ID}|${CMAKE_C_COMPILER_VERSION}|${CMAKE_C_FLAGS}|${CMAKE_C_FLAGS_DEBUG}|${CMAKE_C_FLAGS_RELEASE}|${ORBITER_MATH_FORCE_SSE2}")
foreach(_native_source IN LISTS _native_sources)
    get_filename_component(_native_absolute "${_native_source}" ABSOLUTE BASE_DIR "${CMAKE_CURRENT_SOURCE_DIR}")
    set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${_native_absolute}")
    file(SHA256 "${_native_absolute}" _native_hash)
    string(APPEND _native_input "|${_native_hash}")
endforeach()
string(SHA256 ORBITER_NATIVE_BUILD_BASE "${_native_input}")
configure_file(NativeBuild.h.in "${CMAKE_CURRENT_BINARY_DIR}/native-sdk/OrbiterNativeBuild.h" @ONLY)
target_include_directories(orbiter_production_boundary PUBLIC "${CMAKE_CURRENT_BINARY_DIR}/native-sdk")

# Windows has no ELF-style build RPATH. Every executable that consumes this
# library must stage its runtime beside itself, including nested test targets.
function(orbiter_stage_core_runtime target)
    if(WIN32)
        add_custom_command(TARGET ${target} POST_BUILD
            COMMAND ${CMAKE_COMMAND} -E copy_if_different
                $<TARGET_FILE:orbiter_production_boundary> $<TARGET_FILE_DIR:${target}>)
    endif()
endfunction()
if(DEFINED ORBITER_BINARY_ROOT_DIR)
    set_target_properties(orbiter_production_boundary PROPERTIES
        RUNTIME_OUTPUT_DIRECTORY "${ORBITER_BINARY_ROOT_DIR}")
    install(TARGETS orbiter_production_boundary RUNTIME DESTINATION "${ORBITER_INSTALL_ROOT_DIR}")
else()
    install(TARGETS orbiter_production_boundary LIBRARY DESTINATION lib RUNTIME DESTINATION bin)
endif()
if(ORBITER_BUILD_NATIVE_VESSELS)
    include(NativeVessels.cmake)
endif()
if(ORBITER_BUILD_NATIVE_CELESTIAL_MODULES)
    include(NativeCelestialModules.cmake)
endif()
if(CMAKE_SOURCE_DIR STREQUAL CMAKE_CURRENT_SOURCE_DIR AND BUILD_TESTING)
    add_subdirectory("${CMAKE_CURRENT_SOURCE_DIR}/../../../Tests/Production/Boundary" tests)
endif()
