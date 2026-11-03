# Internal integration candidate. The accepted external-view target remains the
# default until cockpit runtime comparisons have passed.
include(FetchContent)
set(ORBITER_NATIVE_UI_ARCHIVE "" CACHE FILEPATH "Verified pinned ImGui archive (offline builds)")
file(READ "${CMAKE_CURRENT_LIST_DIR}/../../../OVP/OGLClient/dependencies.lock.json" _ui_lock)
string(JSON _ui_hash GET "${_ui_lock}" imgui sha256)
string(JSON _ui_url GET "${_ui_lock}" imgui url)
if(ORBITER_NATIVE_UI_ARCHIVE)
    set(_ui_url "${ORBITER_NATIVE_UI_ARCHIVE}")
endif()
FetchContent_Declare(native_imgui URL "${_ui_url}" URL_HASH "SHA256=${_ui_hash}" DOWNLOAD_EXTRACT_TIMESTAMP TRUE SOURCE_SUBDIR no-build)
FetchContent_MakeAvailable(native_imgui)
target_sources(orbiter_production_vessels PRIVATE
    NativeCockpitProjection.cpp NativeCockpitGui.cpp NativeCockpitVessel.cpp ../Astro.cpp
    ../Pane.cpp ../hud.cpp ../Defpanel.cpp ../Panel2D.cpp ../VCockpit.cpp ../Select.cpp
    ../Mfd.cpp ../VectorMap.cpp ../MfdOrbit.cpp ../MfdSurface.cpp ../MfdMap.cpp ../MfdHsi.cpp
    ../MfdLanding.cpp ../MfdDocking.cpp ../MfdAlign.cpp ../MfdSync.cpp ../MfdTransfer.cpp ../MfdComms.cpp
    "${native_imgui_SOURCE_DIR}/imgui.cpp" "${native_imgui_SOURCE_DIR}/imgui_draw.cpp"
    "${native_imgui_SOURCE_DIR}/imgui_tables.cpp" "${native_imgui_SOURCE_DIR}/imgui_widgets.cpp")
target_include_directories(orbiter_production_vessels PRIVATE "${native_imgui_SOURCE_DIR}")
target_compile_definitions(orbiter_production_vessels PUBLIC ORBITER_NATIVE_COCKPIT)

# Stock DG sources refer to meshc-generated group IDs in all four meshes.
add_subdirectory("${CMAKE_CURRENT_LIST_DIR}/../../../Utils/meshc" "${PROJECT_BINARY_DIR}/meshc-native")
set(_dg_mesh_root "${CMAKE_CURRENT_LIST_DIR}/../../Vessel/DeltaGlider/Meshes")
set(_dg_header_dir "${PROJECT_BINARY_DIR}/native-dg-include")
file(MAKE_DIRECTORY "${_dg_header_dir}")
function(native_dg_mesh_header mesh suffix header)
    add_custom_command(OUTPUT "${_dg_header_dir}/${header}"
        COMMAND meshc /I "${_dg_mesh_root}/${mesh}" /P "${suffix}" /O "${_dg_header_dir}/${header}"
        DEPENDS meshc "${_dg_mesh_root}/${mesh}" VERBATIM)
endfunction()
native_dg_mesh_header(deltaglider.msh - meshres.h)
native_dg_mesh_header(deltaglider_vc.msh _VC meshres_vc.h)
native_dg_mesh_header(dg_2dpanel0.msh _P0 meshres_p0.h)
native_dg_mesh_header(dg_2dpanel1.msh _P1 meshres_p1.h)
add_custom_target(native_dg_mesh_resources DEPENDS
    "${_dg_header_dir}/meshres.h" "${_dg_header_dir}/meshres_vc.h"
    "${_dg_header_dir}/meshres_p0.h" "${_dg_header_dir}/meshres_p1.h")
