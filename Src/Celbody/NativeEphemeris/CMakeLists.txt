# Optional native versions of Orbiter's original Earth and Moon ephemerides.
cmake_minimum_required(VERSION 3.24)
project(OrbiterNativeLegacyEphemerides LANGUAGES CXX)
find_package(Python3 REQUIRED COMPONENTS Interpreter)
set(ORBITER_ENGINE_BUILD "" CACHE PATH "Matching native production engine build")
if(NOT EXISTS "${ORBITER_ENGINE_BUILD}/native-sdk/OrbiterNativeBuild.h")
    message(FATAL_ERROR "Configure the production engine first and set ORBITER_ENGINE_BUILD")
endif()
set(source "${CMAKE_CURRENT_SOURCE_DIR}/..")
set(inputs Vsop87/Earth/Earth.cpp Vsop87/Earth/Earth.h Vsop87/Vsop87.cpp
    Vsop87/Vsop87.h Moon/Moon.cpp Moon/ELP82.cpp)
foreach(input IN LISTS inputs)
    get_filename_component(name "${input}" NAME)
    list(APPEND outputs "${CMAKE_CURRENT_BINARY_DIR}/${name}")
    list(APPEND originals "${source}/${input}")
endforeach()
add_custom_command(OUTPUT ${outputs}
    COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/prepare.py"
        "${source}" "${CMAKE_CURRENT_BINARY_DIR}"
    DEPENDS prepare.py ${originals}
    VERBATIM)
add_library(Earth MODULE "${CMAKE_CURRENT_BINARY_DIR}/Earth.cpp" "${CMAKE_CURRENT_BINARY_DIR}/Vsop87.cpp")
add_library(Moon MODULE "${CMAKE_CURRENT_BINARY_DIR}/Moon.cpp" "${CMAKE_CURRENT_BINARY_DIR}/ELP82.cpp")
foreach(body IN ITEMS Earth Moon)
    target_compile_features(${body} PRIVATE cxx_std_17)
    target_compile_definitions(${body} PRIVATE ORBITER_NATIVE_BUILD_CONFIGURATION="$<CONFIG>")
    target_include_directories(${body} PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}"
        "${source}/../Orbiter" "${source}/../../Orbitersdk/include" "${ORBITER_ENGINE_BUILD}/native-sdk")
    target_link_libraries(${body} PRIVATE
        "${ORBITER_ENGINE_BUILD}/${CMAKE_SHARED_LIBRARY_PREFIX}orbiter_production_boundary${CMAKE_SHARED_LIBRARY_SUFFIX}")
    if(CMAKE_SYSTEM_NAME STREQUAL "Linux")
        target_link_options(${body} PRIVATE -Wl,--no-undefined)
    endif()
    set_target_properties(${body} PROPERTIES PREFIX "" CXX_VISIBILITY_PRESET hidden
        LIBRARY_OUTPUT_DIRECTORY "${ORBITER_ENGINE_BUILD}/NativeModules/Celbody")
endforeach()
