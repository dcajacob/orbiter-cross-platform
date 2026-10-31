# Internal shared production boundary. This is not yet the complete engine.
if(CMAKE_SOURCE_DIR STREQUAL CMAKE_CURRENT_SOURCE_DIR)
    cmake_minimum_required(VERSION 3.19)
    project(OrbiterProductionBoundary LANGUAGES CXX)
    include(CTest)
endif()
add_library(orbiter_production_boundary SHARED
    Session.cpp ResourceResolver.cpp MeshData.cpp BodyServices.cpp
    ../Body.cpp ../Vecmat.cpp ../TimeData.cpp ../ConfigFile.cpp)
target_compile_features(orbiter_production_boundary PUBLIC cxx_std_17)
target_compile_definitions(orbiter_production_boundary
    PUBLIC ORBITER_PRODUCTION_SHARED PRIVATE ORBITER_PRODUCTION_BUILD)
target_include_directories(orbiter_production_boundary PUBLIC "${CMAKE_CURRENT_SOURCE_DIR}/..")
set_target_properties(orbiter_production_boundary PROPERTIES
    CXX_EXTENSIONS OFF FOLDER Core WINDOWS_EXPORT_ALL_SYMBOLS ON)

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
if(CMAKE_SOURCE_DIR STREQUAL CMAKE_CURRENT_SOURCE_DIR AND BUILD_TESTING)
    add_subdirectory("${CMAKE_CURRENT_SOURCE_DIR}/../../../Tests/Production/Boundary" tests)
endif()
