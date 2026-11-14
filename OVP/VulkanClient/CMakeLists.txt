cmake_minimum_required(VERSION 3.24)
project(OrbiterVulkanClient LANGUAGES CXX)

find_package(SDL3 3.4 CONFIG REQUIRED)
set(ORBITER_ENGINE_BUILD "" CACHE PATH "Matching Orbiter production engine build")
set(ORBITER_TEST_RUNTIME "" CACHE PATH "Matching Windows Orbiter runtime and SDK")
set(ORBITER_IMGUI_SOURCE "" CACHE PATH "Dear ImGui headers from the matching Windows Orbiter build")
set(ORBITER_VULKAN_PREBUILT_SHADERS "" CACHE PATH "Optional directory with shaders compiled for this revision")
set(ORBITER_VULKAN_SOURCE_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../.." CACHE PATH "Orbiter source checkout")

if(ORBITER_VULKAN_PREBUILT_SHADERS)
    set(shader_dir "${ORBITER_VULKAN_PREBUILT_SHADERS}")
else()
    find_program(GLSLANG_VALIDATOR glslangValidator REQUIRED)
    set(shader_dir "${CMAKE_CURRENT_BINARY_DIR}")
    foreach(stage vert frag)
        add_custom_command(OUTPUT "${shader_dir}/Ship.${stage}.spv"
            COMMAND "${GLSLANG_VALIDATOR}" -V "${CMAKE_CURRENT_SOURCE_DIR}/shaders/Ship.${stage}"
                    -o "${shader_dir}/Ship.${stage}.spv"
            DEPENDS "shaders/Ship.${stage}" VERBATIM)
    endforeach()
endif()

set(shader_header "${CMAKE_CURRENT_BINARY_DIR}/ShipShaders.h")
add_custom_command(OUTPUT "${shader_header}"
    COMMAND "${CMAKE_COMMAND}" "-DSHADER_DIR=${shader_dir}" "-DOUTPUT=${shader_header}"
            -P "${CMAKE_CURRENT_SOURCE_DIR}/EmbedShaders.cmake"
    DEPENDS "${shader_dir}/Ship.vert.spv" "${shader_dir}/Ship.frag.spv" EmbedShaders.cmake
    VERBATIM)
add_library(VulkanClient MODULE VulkanScene.cpp OrbiterScene.cpp "${shader_header}")
target_compile_features(VulkanClient PRIVATE cxx_std_17)
target_include_directories(VulkanClient PRIVATE "${CMAKE_CURRENT_BINARY_DIR}")
target_link_libraries(VulkanClient PRIVATE SDL3::SDL3)
set_target_properties(VulkanClient PROPERTIES PREFIX "")

if(WIN32)
    target_sources(VulkanClient PRIVATE WindowsClient.cpp)
    target_compile_definitions(VulkanClient PRIVATE NOMINMAX WIN32_LEAN_AND_MEAN)
    target_include_directories(VulkanClient PRIVATE
        "${ORBITER_TEST_RUNTIME}/Orbitersdk/include" "${ORBITER_IMGUI_SOURCE}")
    target_link_libraries(VulkanClient PRIVATE user32
        "${ORBITER_TEST_RUNTIME}/Orbitersdk/lib/Orbiter.lib"
        "${ORBITER_TEST_RUNTIME}/Orbitersdk/lib/Orbitersdk.lib")
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
