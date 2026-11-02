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
