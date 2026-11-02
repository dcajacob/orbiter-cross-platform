# A separately built native module using the same production OpenGL scene code.
cmake_minimum_required(VERSION 3.24)
project(OrbiterNativeOpenGLClient LANGUAGES C CXX)
if(WIN32)
    message(FATAL_ERROR "Use the parent Windows GraphicsClient adapter on Windows")
endif()
include(FetchContent)
find_package(OpenGL REQUIRED)
set(ORBITER_ENGINE_BUILD "" CACHE PATH "Matching production engine build")
set(ORBITER_RENDERER_DEPENDENCIES "" CACHE PATH "Verified pinned dependency archive cache")
get_filename_component(ORBITER_ENGINE_BUILD "${ORBITER_ENGINE_BUILD}" ABSOLUTE)
get_filename_component(ORBITER_RENDERER_DEPENDENCIES "${ORBITER_RENDERER_DEPENDENCIES}" ABSOLUTE)
get_filename_component(ORBITER_SOURCE_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../../.." ABSOLUTE)
if(NOT EXISTS "${ORBITER_ENGINE_BUILD}/native-sdk/OrbiterNativeBuild.h")
    message(FATAL_ERROR "A matching native production SDK build is required")
endif()
add_library(native_engine SHARED IMPORTED)
set_target_properties(native_engine PROPERTIES IMPORTED_LOCATION "${ORBITER_ENGINE_BUILD}/liborbiter_production_vessels.so"
    INTERFACE_INCLUDE_DIRECTORIES "${ORBITER_SOURCE_ROOT}/Src/Orbiter;${ORBITER_SOURCE_ROOT}/Orbitersdk/include;${ORBITER_ENGINE_BUILD}/native-sdk"
    INTERFACE_COMPILE_DEFINITIONS "ORBITER_PRODUCTION_SHARED;ORBITER_NATIVE_BUILD_CONFIGURATION=\"${CMAKE_BUILD_TYPE}\"")
add_library(native_boundary SHARED IMPORTED)
set_target_properties(native_boundary PROPERTIES IMPORTED_LOCATION "${ORBITER_ENGINE_BUILD}/liborbiter_production_boundary.so")
set(CMAKE_POSITION_INDEPENDENT_CODE ON)
file(READ "${CMAKE_CURRENT_SOURCE_DIR}/../dependencies.lock.json" dependency_lock)
set(GLM_BUILD_TESTS OFF CACHE BOOL "" FORCE)
set(FT_DISABLE_ZLIB ON CACHE BOOL "" FORCE)
set(FT_DISABLE_BZIP2 ON CACHE BOOL "" FORCE)
set(FT_DISABLE_PNG ON CACHE BOOL "" FORCE)
set(FT_DISABLE_HARFBUZZ ON CACHE BOOL "" FORCE)
set(FT_DISABLE_BROTLI ON CACHE BOOL "" FORCE)
set(BUILD_SHARED_LIBS OFF CACHE BOOL "" FORCE)
foreach(name glm freetype soil2 nanovg libnsbmp imgui zlib)
    string(JSON checksum GET "${dependency_lock}" "${name}" sha256)
    if(name STREQUAL "glm" OR name STREQUAL "freetype" OR name STREQUAL "zlib")
        FetchContent_Declare(${name} URL "${ORBITER_RENDERER_DEPENDENCIES}/${name}.zip" URL_HASH "SHA256=${checksum}" DOWNLOAD_EXTRACT_TIMESTAMP TRUE)
    else()
        FetchContent_Declare(${name} URL "${ORBITER_RENDERER_DEPENDENCIES}/${name}.zip" URL_HASH "SHA256=${checksum}" DOWNLOAD_EXTRACT_TIMESTAMP TRUE SOURCE_SUBDIR no-build)
    endif()
endforeach()
set(GLFW_BUILD_EXAMPLES OFF CACHE BOOL "" FORCE)
set(GLFW_BUILD_TESTS OFF CACHE BOOL "" FORCE)
set(GLFW_BUILD_DOCS OFF CACHE BOOL "" FORCE)
set(GLFW_INSTALL OFF CACHE BOOL "" FORCE)
set(GLFW_LIBRARY_TYPE STATIC CACHE STRING "" FORCE)
FetchContent_Declare(glfw URL "${ORBITER_RENDERER_DEPENDENCIES}/glfw.tar.gz"
    URL_HASH SHA256=5234f4f29473e9a06bc7847d8371858dd135d38466eeeaa652fdc9f8f9ff0c20 DOWNLOAD_EXTRACT_TIMESTAMP TRUE)
set(CMAKE_POLICY_VERSION_MINIMUM 3.5)
FetchContent_MakeAvailable(glm freetype soil2 nanovg libnsbmp imgui zlib glfw)
add_library(orbiter_ogl_native MODULE
    LinuxAdapter.cpp NativeEvidence.cpp
    ../OGLClient.cpp ../Shader.cpp ../CelSphere.cpp ../Renderer.cpp ../VertexBuffer.cpp ../Scene.cpp ../Light.cpp
    ../OGLCamera.cpp ../OGLMesh.cpp ../MeshManager.cpp ../VObject.cpp ../VVessel.cpp ../Texture.cpp ../VPlanet.cpp ../VStar.cpp ../ztreemgr.cpp
    ../TileMgr.cpp ../SurfMgr.cpp ../RingMgr.cpp ../HazeMgr.cpp ../CloudMgr.cpp ../tilemgr2.cpp ../surfmgr2.cpp ../tilelabel.cpp
    ../VBase.cpp ../cloudmgr2.cpp ../Particle.cpp ../CSphereMgr.cpp ../spherepatch.cpp ../OGLPad.cpp ../glad.c
    "${nanovg_SOURCE_DIR}/src/nanovg.c"
    "${soil2_SOURCE_DIR}/srcs/etc1_utils.c" "${soil2_SOURCE_DIR}/srcs/image_DXT.c"
    "${soil2_SOURCE_DIR}/srcs/image_helper.c" "${soil2_SOURCE_DIR}/srcs/SOIL2.c"
    "${libnsbmp_SOURCE_DIR}/src/libnsbmp.c")
target_compile_features(orbiter_ogl_native PRIVATE cxx_std_17)
target_compile_definitions(orbiter_ogl_native PRIVATE GLFW_INCLUDE_NONE NVG_NO_STB=1 FONS_USE_FREETYPE=1)
target_include_directories(orbiter_ogl_native PRIVATE ..
    "${soil2_SOURCE_DIR}/incs" "${soil2_SOURCE_DIR}/srcs" "${nanovg_SOURCE_DIR}/src"
    "${libnsbmp_SOURCE_DIR}/include" "${imgui_SOURCE_DIR}" "${imgui_SOURCE_DIR}/backends")
target_link_libraries(orbiter_ogl_native PRIVATE native_engine native_boundary glm::glm freetype zlibstatic glfw OpenGL::GL ${CMAKE_DL_LIBS})
target_link_options(orbiter_ogl_native PRIVATE -Wl,--no-undefined -Wl,--exclude-libs,ALL)
set_target_properties(orbiter_ogl_native PROPERTIES PREFIX "" OUTPUT_NAME OGLClient
    LIBRARY_OUTPUT_DIRECTORY "${ORBITER_ENGINE_BUILD}/NativeModules/Graphics" BUILD_RPATH "${ORBITER_ENGINE_BUILD}"
    CXX_VISIBILITY_PRESET hidden C_VISIBILITY_PRESET hidden VISIBILITY_INLINES_HIDDEN YES)

# Preserve the same donor/dependency attribution with the separately linked module.
set(native_notices "${ORBITER_ENGINE_BUILD}/NativeModules/Graphics/Licenses")
file(MAKE_DIRECTORY "${native_notices}")
configure_file("${CMAKE_CURRENT_SOURCE_DIR}/../ATTRIBUTION.md" "${native_notices}/OpenGL-ATTRIBUTION.md" COPYONLY)
configure_file("${CMAKE_CURRENT_SOURCE_DIR}/../dependencies.lock.json" "${native_notices}/dependencies.lock.json" COPYONLY)
configure_file("${ORBITER_SOURCE_ROOT}/LICENSE" "${native_notices}/Orbiter-MIT.txt" COPYONLY)
foreach(notice "${glm_SOURCE_DIR}/copying.txt" "${freetype_SOURCE_DIR}/docs/FTL.TXT"
    "${nanovg_SOURCE_DIR}/LICENSE.txt" "${libnsbmp_SOURCE_DIR}/COPYING" "${soil2_SOURCE_DIR}/README.md"
    "${imgui_SOURCE_DIR}/LICENSE.txt" "${glfw_SOURCE_DIR}/LICENSE.md" "${zlib_SOURCE_DIR}/zlib.h")
    get_filename_component(name "${notice}" NAME)
    get_filename_component(parent "${notice}" DIRECTORY)
    get_filename_component(component "${parent}" NAME)
    configure_file("${notice}" "${native_notices}/${component}-${name}" COPYONLY)
endforeach()

set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${ORBITER_ENGINE_BUILD}/native-sdk/OrbiterNativeBuild.h")
file(STRINGS "${ORBITER_ENGINE_BUILD}/native-sdk/OrbiterNativeBuild.h" cockpit_define
    REGEX "^#define ORBITER_BUILD_NATIVE_COCKPIT 1$")
if(cockpit_define)
    find_package(X11 REQUIRED)
    target_include_directories(orbiter_ogl_native PRIVATE ${X11_INCLUDE_DIR} ${X11_Xrandr_INCLUDE_PATH})
    target_link_libraries(orbiter_ogl_native PRIVATE X11::X11)
    target_sources(orbiter_ogl_native PRIVATE
        "${imgui_SOURCE_DIR}/backends/imgui_impl_glfw.cpp"
        "${imgui_SOURCE_DIR}/backends/imgui_impl_opengl3.cpp")
endif()
