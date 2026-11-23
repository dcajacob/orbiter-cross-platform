cmake_minimum_required(VERSION 3.24)
project(OrbiterVulkanClient LANGUAGES CXX)

find_package(Threads REQUIRED)
find_package(SDL3 3.4 CONFIG REQUIRED)
set(ORBITER_ENGINE_BUILD "" CACHE PATH "Matching Orbiter production engine build")
set(ORBITER_TEST_RUNTIME "" CACHE PATH "Matching Windows Orbiter runtime and SDK")
set(ORBITER_IMGUI_SOURCE "" CACHE PATH "Dear ImGui source tree used by the matching Orbiter build")
set(ORBITER_VULKAN_PREBUILT_SHADERS "" CACHE PATH "Optional directory with shaders compiled for this revision")
set(ORBITER_VULKAN_SOURCE_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../.." CACHE PATH "Orbiter source checkout")

if(ORBITER_VULKAN_PREBUILT_SHADERS)
    set(shader_dir "${ORBITER_VULKAN_PREBUILT_SHADERS}")
else()
    find_program(GLSLANG_VALIDATOR glslangValidator REQUIRED)
    set(shader_dir "${CMAKE_CURRENT_BINARY_DIR}")
endif()
set(shader_sources Ship.vert Ship.frag Earth.frag Sky.vert Sky.frag Terrain.frag BaseDepth.vert BaseDepth.frag Panel.vert Panel.frag)
foreach(shader IN LISTS shader_sources)
    set(object "${shader_dir}/${shader}.spv")
    list(APPEND shader_objects "${object}")
    if(NOT ORBITER_VULKAN_PREBUILT_SHADERS)
        add_custom_command(OUTPUT "${object}"
            COMMAND "${GLSLANG_VALIDATOR}" -V "${CMAKE_CURRENT_SOURCE_DIR}/shaders/${shader}" -o "${object}"
            DEPENDS "shaders/${shader}" shaders/EarthAir.glsl VERBATIM)
    endif()
endforeach()

# Embed the stock Lekton glyph atlas in the client, alongside the shaders.
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS CockpitFont.png)
file(READ "${CMAKE_CURRENT_SOURCE_DIR}/CockpitFont.png" cockpit_font HEX)
string(REGEX REPLACE "(..)" "0x\\1," cockpit_font "${cockpit_font}")
file(CONFIGURE OUTPUT "${CMAKE_CURRENT_BINARY_DIR}/CockpitFontData.h"
    CONTENT "constexpr unsigned char cockpitFontPng[] = { @cockpit_font@ };")

set(shader_header "${CMAKE_CURRENT_BINARY_DIR}/ShipShaders.h")
add_custom_command(OUTPUT "${shader_header}"
    COMMAND "${CMAKE_COMMAND}" "-DSHADER_DIR=${shader_dir}" "-DOUTPUT=${shader_header}" "-DSHADERS=${shader_sources}"
            -P "${CMAKE_CURRENT_SOURCE_DIR}/EmbedShaders.cmake"
    DEPENDS ${shader_objects} EmbedShaders.cmake
    VERBATIM)
add_library(VulkanClient MODULE CockpitSketchpad.cpp Panel.cpp VulkanScene.cpp OrbiterScene.cpp RunwayTerrain.cpp VesselPose.cpp "${shader_header}")
target_compile_features(VulkanClient PRIVATE cxx_std_17)
target_include_directories(VulkanClient PRIVATE "${CMAKE_CURRENT_BINARY_DIR}")
target_link_libraries(VulkanClient PRIVATE SDL3::SDL3 Threads::Threads)
set_target_properties(VulkanClient PROPERTIES PREFIX "")

if(NOT WIN32 AND EXISTS "${ORBITER_ENGINE_BUILD}/native-sdk/OrbiterNativeBuild.h")
    set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${ORBITER_ENGINE_BUILD}/native-sdk/OrbiterNativeBuild.h")
    file(STRINGS "${ORBITER_ENGINE_BUILD}/native-sdk/OrbiterNativeBuild.h" native_cockpit
        REGEX "^#define ORBITER_BUILD_NATIVE_COCKPIT 1$")
endif()
if(WIN32 OR native_cockpit)
    if(NOT ORBITER_IMGUI_SOURCE AND NOT WIN32)
        set(ORBITER_IMGUI_SOURCE "${ORBITER_ENGINE_BUILD}/_deps/native_imgui-src")
    endif()
    if(NOT EXISTS "${ORBITER_IMGUI_SOURCE}/backends/imgui_impl_sdlgpu3.cpp")
        message(FATAL_ERROR "Set ORBITER_IMGUI_SOURCE to the matching Orbiter Dear ImGui source tree, including backends")
    endif()
    target_include_directories(VulkanClient PRIVATE "${ORBITER_IMGUI_SOURCE}" "${ORBITER_IMGUI_SOURCE}/backends")
    target_sources(VulkanClient PRIVATE "${ORBITER_IMGUI_SOURCE}/backends/imgui_impl_sdlgpu3.cpp")
    target_compile_definitions(VulkanClient PRIVATE ORBITER_VULKAN_IMGUI)
    if(NOT WIN32)
        target_sources(VulkanClient PRIVATE "${ORBITER_IMGUI_SOURCE}/backends/imgui_impl_sdl3.cpp")
    endif()
endif()

if(WIN32)
    target_sources(VulkanClient PRIVATE WindowsClient.cpp)
    target_compile_definitions(VulkanClient PRIVATE NOMINMAX WIN32_LEAN_AND_MEAN ORBITER_PRODUCTION_SHARED)
    target_include_directories(VulkanClient PRIVATE
        "${ORBITER_TEST_RUNTIME}/Orbitersdk/include" "${ORBITER_IMGUI_SOURCE}"
        "${ORBITER_VULKAN_SOURCE_ROOT}/Src/Orbiter")
    target_link_libraries(VulkanClient PRIVATE user32
        "${ORBITER_TEST_RUNTIME}/Orbitersdk/lib/Orbiter.lib"
        "${ORBITER_TEST_RUNTIME}/Orbitersdk/lib/Orbitersdk.lib"
        "${ORBITER_TEST_RUNTIME}/Src/Orbiter/Production/orbiter_production_boundary.lib")
else()
    if(NOT EXISTS "${ORBITER_ENGINE_BUILD}/native-sdk/OrbiterNativeBuild.h")
        message(FATAL_ERROR "Configure against the matching native production SDK build")
    endif()
    target_sources(VulkanClient PRIVATE LinuxClient.cpp)
    target_compile_definitions(VulkanClient PRIVATE ORBITER_PRODUCTION_SHARED
        ORBITER_NATIVE_BUILD_CONFIGURATION="$<CONFIG>")
    target_include_directories(VulkanClient PRIVATE
        "${ORBITER_VULKAN_SOURCE_ROOT}/Src/Orbiter"
        "${ORBITER_VULKAN_SOURCE_ROOT}/Orbitersdk/include"
        "${ORBITER_ENGINE_BUILD}/native-sdk")
    target_link_libraries(VulkanClient PRIVATE
        "${ORBITER_ENGINE_BUILD}/liborbiter_production_vessels.so"
        "${ORBITER_ENGINE_BUILD}/liborbiter_production_boundary.so")
    target_link_options(VulkanClient PRIVATE -Wl,--no-undefined)
endif()

install(FILES Cockpit/deltaglider_vc.msh DESTINATION Meshes/Vulkan/DG COMPONENT DeltaGliderCockpit)
install(FILES Cockpit/dg_flightdeck.dds Cockpit/dg_flightdeck_surface.dds
    DESTINATION Textures/DG COMPONENT DeltaGliderCockpit)
install(FILES ISSManualDock.scn DESTINATION Scenarios/Vulkan COMPONENT DeltaGliderCockpit)
install(FILES AtlantisGrapple.scn AtlantisRMS.scn DESTINATION Scenarios/Vulkan COMPONENT AtlantisGrapple)
install(FILES AtlantisGrapple.lua DESTINATION Script COMPONENT AtlantisGrapple)
