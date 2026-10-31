# Selective adaptation of TheGondos/orbiter ad964944, original MIT notices retained.
cmake_minimum_required(VERSION 3.24)
project(OrbiterOpenGLClient LANGUAGES C CXX)
if(NOT WIN32 OR NOT MSVC)
  message(FATAL_ERROR "This delivery implements the existing Windows GraphicsClient adapter; the native adapter follows the production engine boundary")
endif()
include(FetchContent)
set(ORBITER_TEST_RUNTIME "" CACHE PATH "Verified same-build Windows application and SDK")
set(DXSDK_DIR "$ENV{DXSDK_DIR}" CACHE PATH "Existing Windows SDK dependency")
get_filename_component(ORBITER_TEST_RUNTIME "${ORBITER_TEST_RUNTIME}" ABSOLUTE)
if(NOT EXISTS "${ORBITER_TEST_RUNTIME}/Orbitersdk/lib/Orbiter.lib")
  message(FATAL_ERROR "The separately built client requires the source-built Orbiter SDK/runtime")
endif()
file(READ "${CMAKE_CURRENT_SOURCE_DIR}/dependencies.lock.json" dependency_lock)
function(pin name)
  string(JSON url GET "${dependency_lock}" "${name}" url)
  string(JSON checksum GET "${dependency_lock}" "${name}" sha256)
  if(name STREQUAL "glm" OR name STREQUAL "freetype" OR name STREQUAL "zlib")
    FetchContent_Declare(${name} URL "${url}" URL_HASH "SHA256=${checksum}" DOWNLOAD_EXTRACT_TIMESTAMP TRUE)
  else()
    FetchContent_Declare(${name} URL "${url}" URL_HASH "SHA256=${checksum}" DOWNLOAD_EXTRACT_TIMESTAMP TRUE SOURCE_SUBDIR no-build)
  endif()
endfunction()
set(GLM_BUILD_TESTS OFF CACHE BOOL "" FORCE)
set(FT_DISABLE_ZLIB ON CACHE BOOL "" FORCE)
set(FT_DISABLE_BZIP2 ON CACHE BOOL "" FORCE)
set(FT_DISABLE_PNG ON CACHE BOOL "" FORCE)
set(FT_DISABLE_HARFBUZZ ON CACHE BOOL "" FORCE)
set(FT_DISABLE_BROTLI ON CACHE BOOL "" FORCE)
set(BUILD_SHARED_LIBS OFF CACHE BOOL "" FORCE)
foreach(name glm freetype soil2 nanovg libnsbmp imgui zlib)
  pin(${name})
endforeach()
FetchContent_MakeAvailable(glm freetype soil2 nanovg libnsbmp imgui zlib)
add_library(OGLClient SHARED
  WindowsAdapter.cpp Evidence.cpp OGLClient.cpp Shader.cpp CelSphere.cpp Renderer.cpp VertexBuffer.cpp Scene.cpp Light.cpp
  OGLCamera.cpp OGLMesh.cpp MeshManager.cpp VObject.cpp VVessel.cpp Texture.cpp VPlanet.cpp VStar.cpp ztreemgr.cpp
  TileMgr.cpp SurfMgr.cpp RingMgr.cpp HazeMgr.cpp CloudMgr.cpp tilemgr2.cpp surfmgr2.cpp tilelabel.cpp
  VBase.cpp cloudmgr2.cpp Particle.cpp CSphereMgr.cpp spherepatch.cpp OGLPad.cpp glad.c
  "${nanovg_SOURCE_DIR}/src/nanovg.c"
  "${soil2_SOURCE_DIR}/srcs/etc1_utils.c" "${soil2_SOURCE_DIR}/srcs/image_DXT.c"
  "${soil2_SOURCE_DIR}/srcs/image_helper.c" "${soil2_SOURCE_DIR}/srcs/SOIL2.c"
  "${libnsbmp_SOURCE_DIR}/src/libnsbmp.c"
  "${imgui_SOURCE_DIR}/backends/imgui_impl_opengl3.cpp")
target_compile_features(OGLClient PRIVATE cxx_std_17)
target_compile_options(OGLClient PRIVATE /Zi)
target_link_options(OGLClient PRIVATE /DEBUG)
target_compile_options(OGLClient PRIVATE "$<$<COMPILE_LANGUAGE:C>:/FIstdint.h>")
target_compile_definitions(OGLClient PRIVATE NVG_NO_STB=1 FONS_USE_FREETYPE=1 NOMINMAX WIN32_LEAN_AND_MEAN _CRT_SECURE_NO_WARNINGS)
target_compile_definitions(OGLClient PRIVATE "IMGUI_USER_CONFIG=\"${CMAKE_CURRENT_SOURCE_DIR}/../../Extern/imgui/imconfig.h\"")
target_include_directories(OGLClient PRIVATE
  "${ORBITER_TEST_RUNTIME}/Orbitersdk/include" "${DXSDK_DIR}/Include"
  "${soil2_SOURCE_DIR}/incs" "${soil2_SOURCE_DIR}/srcs" "${nanovg_SOURCE_DIR}/src"
  "${libnsbmp_SOURCE_DIR}/include" "${imgui_SOURCE_DIR}" "${imgui_SOURCE_DIR}/backends" "${zlib_SOURCE_DIR}" "${zlib_BINARY_DIR}")
target_link_libraries(OGLClient PRIVATE glm::glm freetype zlibstatic opengl32 gdi32 user32 dbghelp
  "${ORBITER_TEST_RUNTIME}/Orbitersdk/lib/Orbiter.lib"
  "${ORBITER_TEST_RUNTIME}/Orbitersdk/lib/Orbitersdk.lib")
set_target_properties(OGLClient PROPERTIES RUNTIME_OUTPUT_DIRECTORY "${ORBITER_TEST_RUNTIME}/Modules/Plugin"
  PDB_OUTPUT_DIRECTORY "${ORBITER_TEST_RUNTIME}/Modules/Plugin")
file(GLOB shaders CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/shaders/*")
add_custom_command(TARGET OGLClient POST_BUILD
  COMMAND ${CMAKE_COMMAND} -E make_directory "${ORBITER_TEST_RUNTIME}/Modules/OGLClient"
  COMMAND ${CMAKE_COMMAND} -E copy_if_different ${shaders} "${ORBITER_TEST_RUNTIME}/Modules/OGLClient")
file(MAKE_DIRECTORY "${ORBITER_TEST_RUNTIME}/Modules/OGLClient/Licenses")
file(COPY "${CMAKE_CURRENT_SOURCE_DIR}/dependencies.lock.json" DESTINATION "${ORBITER_TEST_RUNTIME}/Modules/OGLClient")
foreach(notice "${glm_SOURCE_DIR}/copying.txt" "${freetype_SOURCE_DIR}/docs/FTL.TXT"
  "${nanovg_SOURCE_DIR}/LICENSE.txt" "${libnsbmp_SOURCE_DIR}/COPYING"
  "${soil2_SOURCE_DIR}/README.md" "${imgui_SOURCE_DIR}/LICENSE.txt")
  get_filename_component(name "${notice}" NAME)
  get_filename_component(parent "${notice}" DIRECTORY)
  get_filename_component(component "${parent}" NAME)
  configure_file("${notice}" "${ORBITER_TEST_RUNTIME}/Modules/OGLClient/Licenses/${component}-${name}" COPYONLY)
endforeach()
# Carry the original license-bearing source headers as well as standalone
# licenses; embedded notices must accompany the separately linked module.
configure_file("${CMAKE_CURRENT_SOURCE_DIR}/../../LICENSE"
  "${ORBITER_TEST_RUNTIME}/Modules/OGLClient/Licenses/Orbiter-MIT.txt" COPYONLY)
configure_file("${CMAKE_CURRENT_SOURCE_DIR}/ATTRIBUTION.md"
  "${ORBITER_TEST_RUNTIME}/Modules/OGLClient/ATTRIBUTION.md" COPYONLY)
foreach(notice
  "${soil2_SOURCE_DIR}/incs/stb_image.h" "${soil2_SOURCE_DIR}/incs/stb_image_write.h"
  "${nanovg_SOURCE_DIR}/src/fontstash.h" "${zlib_SOURCE_DIR}/zlib.h"
  "${CMAKE_CURRENT_SOURCE_DIR}/Shadinclude.hpp" "${CMAKE_CURRENT_SOURCE_DIR}/OGLPad.cpp")
  get_filename_component(name "${notice}" NAME)
  configure_file("${notice}" "${ORBITER_TEST_RUNTIME}/Modules/OGLClient/Licenses/${name}" COPYONLY)
endforeach()
