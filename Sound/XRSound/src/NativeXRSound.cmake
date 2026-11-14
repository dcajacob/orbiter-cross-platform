find_package(Threads REQUIRED)
set(_xr_dir "${CMAKE_CURRENT_LIST_DIR}")
add_library(native_xrsound MODULE
    "${_xr_dir}/NativeXRSound.cpp" "${_xr_dir}/XRSoundDLL.cpp" "${_xr_dir}/XRSoundEngine.cpp"
    "${_xr_dir}/XRSoundEngine30.cpp" "${_xr_dir}/VesselXRSoundEngine.cpp" "${_xr_dir}/ModuleXRSoundEngine.cpp"
    "${_xr_dir}/SoundPreSteps.cpp" "${_xr_dir}/DefaultSoundGroupPreSteps.cpp"
    "${_xr_dir}/XRSoundConfigFileParser.cpp" "${_xr_dir}/Utils/ConfigFileParser.cpp"
    "${_xr_dir}/Utils/FileList.cpp" "${_xr_dir}/ISound.cpp")
target_include_directories(native_xrsound PRIVATE "${_xr_dir}" "${_xr_dir}/Utils")
target_compile_definitions(native_xrsound PRIVATE XRSOUND_DLL_BUILD MA_NO_NULL)
target_link_libraries(native_xrsound PRIVATE orbiter_production_vessels Threads::Threads ${CMAKE_DL_LIBS} m)
target_link_options(native_xrsound PRIVATE -Wl,--no-undefined)
set_target_properties(native_xrsound PROPERTIES PREFIX "" OUTPUT_NAME XRSound
    LIBRARY_OUTPUT_DIRECTORY "${PROJECT_BINARY_DIR}/NativeModules/Plugin"
    CXX_VISIBILITY_PRESET hidden VISIBILITY_INLINES_HIDDEN ON)
unset(_xr_dir)
