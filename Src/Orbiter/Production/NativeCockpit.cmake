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
    NativeAnnotations.cpp NativeScript.cpp NativeInterpreterSdk.cpp NativeCockpitProjection.cpp NativeCockpitMfd.cpp NativeCockpitGui.cpp ../MenuInfoBar.cpp ../DlgFocus.cpp NativeCockpitVessel.cpp ../CockpitSdk.cpp ../Astro.cpp
    ../Pane.cpp ../hud.cpp ../Defpanel.cpp ../Panel2D.cpp ../VCockpit.cpp ../Select.cpp
    ../Mfd.cpp ../MfdUser.cpp ../VectorMap.cpp ../MfdOrbit.cpp ../MfdSurface.cpp ../MfdMap.cpp ../MfdHsi.cpp
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

# These are the panel elements and subsystem base used by the stock vessel.
set(_dg_source "${CMAKE_CURRENT_LIST_DIR}/../../Vessel/DeltaGlider")
add_library(native_dg_instruments STATIC
    "${_dg_source}/../Common/Instrument.cpp"
    "${_dg_source}/DGSwitches.cpp" "${_dg_source}/FuelMfd.cpp" "${_dg_source}/Horizon.cpp"
    "${_dg_source}/InstrAoa.cpp" "${_dg_source}/InstrHsi.cpp"
    "${_dg_source}/InstrVs.cpp" "${_dg_source}/MomentInd.cpp")
target_include_directories(native_dg_instruments PRIVATE "${_dg_header_dir}")
target_link_libraries(native_dg_instruments PRIVATE orbiter_production_vessels)
set_target_properties(native_dg_instruments PROPERTIES POSITION_INDEPENDENT_CODE ON)
add_dependencies(native_dg_instruments native_dg_mesh_resources)

# Compiled into the stock vessel once its main module and interpreter are linked.
add_library(native_dg_subsystems STATIC
    "${_dg_source}/AAPSubsys.cpp"
    "${_dg_source}/AerodynSubsys.cpp"
    "${_dg_source}/AvionicsSubsys.cpp"
    "${_dg_source}/DockingSubsys.cpp"
    "${_dg_source}/FailureSubsys.cpp"
    "${_dg_source}/GearSubsys.cpp"
    "${_dg_source}/HoverSubsys.cpp"
    "${_dg_source}/HudCtrl.cpp"
    "${_dg_source}/LightSubsys.cpp"
    "${_dg_source}/MainRetroSubsys.cpp"
    "${_dg_source}/MfdSubsys.cpp"
    "${_dg_source}/PressureSubsys.cpp"
    "${_dg_source}/RcsSubsys.cpp"
    "${_dg_source}/ScramSubsys.cpp"
    "${_dg_source}/ThermalSubsys.cpp"
)
target_include_directories(native_dg_subsystems PRIVATE "${_dg_header_dir}")
target_link_libraries(native_dg_subsystems PRIVATE native_dg_instruments orbiter_production_vessels)
set_target_properties(native_dg_subsystems PROPERTIES POSITION_INDEPENDENT_CODE ON)
add_dependencies(native_dg_subsystems native_dg_mesh_resources)

add_library(native_dg_vessel OBJECT "${_dg_source}/DeltaGlider.cpp")
target_include_directories(native_dg_vessel PRIVATE "${_dg_header_dir}" "${native_imgui_SOURCE_DIR}")
target_link_libraries(native_dg_vessel PRIVATE native_dg_subsystems orbiter_production_vessels)
set_target_properties(native_dg_vessel PROPERTIES POSITION_INDEPENDENT_CODE ON)
add_dependencies(native_dg_vessel native_dg_mesh_resources)

add_subdirectory("${CMAKE_CURRENT_LIST_DIR}/../../Module/LuaScript/Native" "${PROJECT_BINARY_DIR}/native-lua")
add_library(native_deltaglider MODULE
    $<TARGET_OBJECTS:native_dg_vessel> $<TARGET_OBJECTS:native_dg_lua_bindings>)
target_link_libraries(native_deltaglider PRIVATE native_dg_subsystems native_lua_script_files lua orbiter_production_vessels)
target_link_options(native_deltaglider PRIVATE -Wl,--no-undefined)
set_target_properties(native_deltaglider PROPERTIES PREFIX "" OUTPUT_NAME DeltaGlider
    LIBRARY_OUTPUT_DIRECTORY "${PROJECT_BINARY_DIR}/NativeModules/Vessel")

add_library(native_lua_inline_list OBJECT ../../Module/LuaScript/LuaInline/LuaInline.cpp)
target_include_directories(native_lua_inline_list PRIVATE "${CMAKE_CURRENT_LIST_DIR}/../../Module/LuaScript/LuaInterpreter")
target_link_libraries(native_lua_inline_list PRIVATE lua orbiter_production_vessels)
set_target_properties(native_lua_inline_list PROPERTIES POSITION_INDEPENDENT_CODE ON)

add_library(native_lua_interpreter_core OBJECT ../../Module/LuaScript/LuaInterpreter/Interpreter.cpp)
target_link_libraries(native_lua_interpreter_core PRIVATE lua orbiter_production_vessels)
set_target_properties(native_lua_interpreter_core PROPERTIES POSITION_INDEPENDENT_CODE ON)

target_link_libraries(orbiter_production_vessels PRIVATE ${_archive_zlib})
target_include_directories(orbiter_production_vessels PRIVATE ${_archive_zlib_includes})

add_library(native_lua_interpreter SHARED
    $<TARGET_OBJECTS:native_lua_interpreter_core> $<TARGET_OBJECTS:native_lua_vessel_bindings>
    ../../Module/LuaScript/LuaInterpreter/InterpreterExecution.cpp)
target_link_libraries(native_lua_interpreter PRIVATE native_lua_script_files lua orbiter_production_vessels)
target_link_options(native_lua_interpreter PRIVATE -Wl,--no-undefined)
set_target_properties(native_lua_interpreter PROPERTIES PREFIX "" OUTPUT_NAME LuaInterpreter
    LIBRARY_OUTPUT_DIRECTORY "${PROJECT_BINARY_DIR}/NativeModules/Plugin")

add_library(native_lua_inline MODULE $<TARGET_OBJECTS:native_lua_inline_list>
    ../../Module/LuaScript/LuaInline/InlineEnvironment.cpp)
target_include_directories(native_lua_inline PRIVATE "${CMAKE_CURRENT_LIST_DIR}/../../Module/LuaScript/LuaInterpreter")
target_link_libraries(native_lua_inline PRIVATE native_lua_interpreter lua orbiter_production_vessels)
target_link_options(native_lua_inline PRIVATE -Wl,--no-undefined)
set_target_properties(native_lua_inline PROPERTIES PREFIX "" OUTPUT_NAME LuaInline
    LIBRARY_OUTPUT_DIRECTORY "${PROJECT_BINARY_DIR}/NativeModules/Plugin")
