# Internal shared production boundary. This is not yet the complete engine.
if(CMAKE_SOURCE_DIR STREQUAL CMAKE_CURRENT_SOURCE_DIR)
    cmake_minimum_required(VERSION 3.19)
    project(OrbiterProductionBoundary LANGUAGES CXX)
    include(CTest)
endif()
add_library(orbiter_production_boundary SHARED
    Session.cpp WorldOwner.cpp NativeModule.cpp ResourceResolver.cpp MeshData.cpp MeshServices.cpp BodyServices.cpp RigidBodyServices.cpp CelestialServices.cpp ScenarioColor.cpp
    ../Body.cpp ../Rigidbody.cpp ../BodyIntegrator.cpp ../Element.cpp
    ../Vecmat.cpp ../TimeData.cpp ../ConfigFile.cpp ../Mesh.cpp ../State.cpp
    ../PinesGrav.cpp ../PinesGravFile.cpp ../Celbody.cpp ../CelbodyFile.cpp ../ElementFile.cpp ../Star.cpp)
target_compile_features(orbiter_production_boundary PUBLIC cxx_std_17)
target_compile_definitions(orbiter_production_boundary
    PUBLIC ORBITER_PRODUCTION_SHARED ORBITER_NATIVE_BUILD_CONFIGURATION="$<CONFIG>" PRIVATE ORBITER_PRODUCTION_BUILD)
target_include_directories(orbiter_production_boundary PUBLIC "${CMAKE_CURRENT_SOURCE_DIR}/.."
    "${CMAKE_CURRENT_SOURCE_DIR}/../../../Orbitersdk/include")
set_target_properties(orbiter_production_boundary PROPERTIES
    CXX_EXTENSIONS OFF FOLDER Core WINDOWS_EXPORT_ALL_SYMBOLS ON)
target_link_libraries(orbiter_production_boundary PRIVATE ${CMAKE_DL_LIBS})

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
set(_native_input "${ORBITER_NATIVE_BUILD_TOKEN}|${CMAKE_CXX_COMPILER_ID}|${CMAKE_CXX_COMPILER_VERSION}|${CMAKE_SYSTEM_NAME}|${CMAKE_SYSTEM_PROCESSOR}|${CMAKE_SIZEOF_VOID_P}|${CMAKE_CXX_FLAGS}|${CMAKE_CXX_FLAGS_DEBUG}|${CMAKE_CXX_FLAGS_RELEASE}|${CMAKE_MSVC_RUNTIME_LIBRARY}")
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
if(CMAKE_SOURCE_DIR STREQUAL CMAKE_CURRENT_SOURCE_DIR AND BUILD_TESTING)
    add_subdirectory("${CMAKE_CURRENT_SOURCE_DIR}/../../../Tests/Production/Boundary" tests)
endif()
