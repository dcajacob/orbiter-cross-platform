"""Build a relocatable SDK from the exact Phase 8 runtime package."""
import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import subprocess
import tarfile
import zipfile

HERE = Path(__file__).resolve().parent
HEADERS = ("NativeVesselFactory.h", "NativeVesselModule.h", "NativeModule.h",
           "ModuleBootstrap.h", "NativeAbi.h", "ResourceResolver.h", "Export.h")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def source_files(repository, commit, names):
    command = ["git", "-C", str(repository), "archive", "--format=tar", commit, *names]
    with tarfile.open(fileobj=io.BytesIO(subprocess.check_output(command))) as archive:
        return {item.name: archive.extractfile(item).read() for item in archive if item.isfile()}


def native_sdk(package, info, repository):
    extension = "dylib" if info["platform"] == "macos" else "so"
    boundary = f"liborbiter_production_boundary.{extension}"
    runtime = ("orbiter-production", boundary, f"liborbiter_production_vessels.{extension}")
    witnesses = (boundary, "NativeModules/Vessel/DeltaGlider.so", "NativeModules/Graphics/OGLClient.so",
                 "NativeModules/Celbody/spice.so")
    with tarfile.open(package) as archive:
        members = {PurePosixPath(item.name).as_posix(): item for item in archive if item.isfile()}
        def read(name):
            return archive.extractfile(members[name]).read()

        manifest = json.loads(read("runtime.json"))
        bindings = {name: digest(read(name)) for name in (*runtime, *witnesses)}
        expected_build = (info["native_build"] + ":Release").encode() + b"\0"
        expected_abi = info["abi"].encode() + b"\0"
        for name in witnesses:
            data = read(name)
            require(expected_build in data and expected_abi in data, f"Build ABI evidence differs: {name}")
    required = ["Orbitersdk/include", "LICENSE"] + [f"Src/Orbiter/Production/{name}" for name in HEADERS]
    files = source_files(repository, info["source"], required)
    sdk = {name.removeprefix("Orbitersdk/"): data for name, data in files.items()
           if name.startswith("Orbitersdk/include/")}
    for name in HEADERS:
        sdk[f"include/Production/{name}"] = files[f"Src/Orbiter/Production/{name}"]
    sdk["LICENSE"] = files["LICENSE"]
    sdk["include/OrbiterNativeBuild.h"] = (
        "// Exact build identity verified in the retained engine and stock modules.\n"
        "#ifndef ORBITER_NATIVE_BUILD_H\n#define ORBITER_NATIVE_BUILD_H\n"
        f'#define ORBITER_NATIVE_BUILD_BASE "{info["native_build"]}"\n'
        "#define ORBITER_BUILD_NATIVE_COCKPIT 1\n#endif\n"
    ).encode()
    return sdk, manifest, bindings


def windows_sdk(package):
    with zipfile.ZipFile(package) as archive:
        manifest = json.loads(archive.read("runtime.json"))
        sdk = {}
        for item in archive.infolist():
            if item.filename.startswith("Orbitersdk/") and not item.is_dir():
                content = archive.read(item)
                require(digest(content) == manifest["files"][item.filename], f"SDK file hash differs: {item.filename}")
                sdk[item.filename.removeprefix("Orbitersdk/")] = content
        sdk["LICENSE"] = archive.read("LICENSE")
        names = ("Orbiter.exe", "Orbitersdk/lib/Orbiter.lib", "Orbitersdk/lib/Orbitersdk.lib",
                 "Orbitersdk/include/Orbitersdk.h")
        bindings = {name: digest(archive.read(name)) for name in names}
    return sdk, manifest, bindings


def build(package, output, repository):
    info = json.loads((HERE / "packages.json").read_text())[package.name]
    with package.open("rb") as stream:
        checksum = hashlib.file_digest(stream, "sha256").hexdigest()
    require(checksum == info["sha256"], "Retained runtime package checksum differs")
    windows = info["platform"] == "windows"
    sdk, manifest, bindings = windows_sdk(package) if windows else native_sdk(package, info, repository)
    require(manifest["source"] == info["source"], "Retained runtime package source differs")
    require(all(manifest["files"][name] == value for name, value in bindings.items()), "Runtime binding hashes differ")
    template = (HERE / "OrbiterSDKConfig.cmake.in").read_text()
    system = {"linux": "Linux", "macos": "Darwin", "windows": "Windows"}[info["platform"]]
    for key, value in {
        "system": system, "arch": info["arch"], "abi": info.get("abi", ""),
        "extension": "dylib" if system == "Darwin" else "so",
        "soname_prefix": "@rpath/" if system == "Darwin" else "",
        "arm_condition": "!defined(__aarch64__)" if info["arch"] == "arm64" else "!defined(__x86_64__)",
        "bindings": " ".join(f'"{name}|{checksum}"' for name, checksum in sorted(bindings.items())),
    }.items():
        template = template.replace(f"@{key}@", value)
    sdk["cmake/OrbiterSDKConfig.cmake"] = template.encode()
    sdk["PACKAGE-SDK.md"] = (HERE / "README.md").read_bytes()
    common = ("CMakeLists.txt",)
    platform = ("Vessel.cpp", "Phase8SdkProbe.cfg") if windows else ("NativeShuttlePBFactory.inc",)
    for name in (*common, *platform):
        sdk[f"example/{name}"] = (HERE / "Example" / name).read_bytes()
    if not windows:
        name = "Src/Vessel/ShuttlePB/ShuttlePB.cpp"
        sdk["example/ShuttlePB.cpp"] = source_files(repository, info["source"], [name])[name]
    report = dict(package=package.name, package_sha256=checksum, package_source=info["source"],
                  platform=info["platform"], architecture=info["arch"], configuration="Release",
                  runtime_bindings=bindings, native_build=info.get("native_build"), abi=info.get("abi"),
                  windows_compiler=info.get("compiler"), files={name: digest(data) for name, data in sorted(sdk.items())})
    sdk["sdk.json"] = (json.dumps(report, indent=2) + "\n").encode()
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "x") as archive:
        for name, data in sorted(sdk.items()):
            archive.writestr(zipfile.ZipInfo(name), data, compress_type=zipfile.ZIP_DEFLATED)
    print(f"Packaged {len(sdk)} SDK files for {package.name}: {output}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-repository", type=Path, default=HERE.parents[1])
    args = parser.parse_args()
    build(args.package, args.output, args.source_repository)


if __name__ == "__main__":
    main()
