// Licensed under the MIT License
#include "Production/Session.h"
#include "Production/ResourceResolver.h"
#include "Production/MeshData.h"
#include "TimeData.h"
#include "Body.h"
#include "OrbiterCelestialData.h"
#include <cstddef>
#include <type_traits>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <cstring>
#include <sstream>
#include <stdexcept>
#include <vector>

static_assert(std::is_standard_layout<ATMPARAM>::value && sizeof(ATMPARAM)==24 && alignof(ATMPARAM)==8);
static_assert(offsetof(ATMPARAM,T)==0 && offsetof(ATMPARAM,p)==8 && offsetof(ATMPARAM,rho)==16);
static_assert(std::is_same<decltype(ATMPARAM::T),double>::value &&
    std::is_same<decltype(ATMPARAM::p),double>::value && std::is_same<decltype(ATMPARAM::rho),double>::value);

using namespace orbiter::production;
namespace fs = std::filesystem;
void require(bool condition, const char* message)
{
    if (!condition) throw std::runtime_error(message);
}
template<class F> void rejects(F action)
{
    bool rejected = false;
    try { action(); } catch (const std::exception&) { rejected = true; }
    require(rejected, "Expected an explicit failure");
}

struct Host final : SessionServices {
    TimeData time;
    bool running = true, playback = false, updating = false, force = true;
    bool stopInPre = false, stopInPost = false, hasVessels = true;
    bool bodiesFinal = false, timeFinal = false;
    std::vector<std::string> events;
    void Observe(const char* event, bool) override
    {
        events.emplace_back(event);
        if (events.back() == "app.frame.end") {
            require(!updating, "Published a state during update");
            require(timeFinal, "Published before time finalization");
            require(!force, "Published before clearing forced update");
        }
    }
    void ModulePreStep() override
    {
        require(!updating, "Pre-step inside state update");
        events.emplace_back("pre");
        if (stopInPre) running = false;
    }
    void PlaybackStep() override { events.emplace_back("playback"); }
    void UpdateBodies(bool forced) override
    {
        require(updating && forced, "Incorrect world update flags");
        events.emplace_back("update");
    }
    void UpdateDialogs() override { events.emplace_back("dialogs"); }
    void ModulePostStep() override
    {
        require(updating, "Post-step outside state update");
        events.emplace_back("post");
        if (stopInPost) running = false;
    }
    bool DeletePendingVessels() override
    {
        require(!updating && !bodiesFinal, "Deletion crossed finalization boundary");
        events.emplace_back("delete");
        return hasVessels;
    }
    void NoVessels() override { events.emplace_back("empty"); }
    void FinaliseBodies() override { bodiesFinal = true; events.emplace_back("finalise"); }
    void AdvanceTime(bool active) override
    {
        require(!active || bodiesFinal, "Time advanced before bodies finalized");
        time.EndStep(active); timeFinal = true; events.emplace_back("time");
    }
    void WriteTrace() override
    {
        require(bodiesFinal && timeFinal, "Trace sampled an unfinished state");
        events.emplace_back("trace");
    }
    void UpdateCamera() override { events.emplace_back("camera"); }
    void UpdatePanels(double sim, double sys) override
    {
        require(sim == time.SimT1 && sys == time.SysT1, "Wrong panel time convention");
        events.emplace_back("panels");
    }
    void UpdateVisuals(bool active) override
    {
        require(active == running, "Visual update used a stale running flag");
        events.emplace_back("visuals");
    }
    void CheckSessionLimit() override { events.emplace_back("limit"); }
    void frame()
    {
        time.Reset(51544.5); time.SetFixedStep(0.25); time.BeginStep(0.01, running);
        Session::UpdateWorld(*this, time, running, playback, updating, force);
        Session::EndTimeStep(*this, time, running, running, force);
    }
};

void sessionTests()
{
    Host h; h.playback = true; h.frame();
    const std::vector<std::string> expected = {
        "world.update.before", "pre", "playback", "update", "dialogs", "post", "delete",
        "world.update.after", "world.finalise.before", "finalise", "world.finalise.after",
        "time.end.before", "time", "time.end.after", "trace", "camera", "panels", "visuals",
        "app.frame.end", "limit"};
    require(h.events == expected, "Production lifecycle order changed");
    require(h.time.SimT0 == 0.25, "Wrong finalized simulation time");
    Host paused; paused.running = false; paused.frame();
    require(paused.time.SimT0 == 0 && !paused.bodiesFinal, "Paused frame advanced physics");
    Host changed; changed.stopInPre = true; changed.hasVessels = false; changed.frame();
    require(!changed.bodiesFinal, "Callback running-state change was ignored");
    require(changed.events[2] == "dialogs" && changed.events[4] == "empty", "Deferred deletion policy changed");
    Host endChanged; endChanged.stopInPost = true; endChanged.frame();
    require(!endChanged.bodiesFinal, "End-step did not receive current running state");
}

void resourceTests(const fs::path& temporary)
{
    auto root = temporary/"resource-fixture";
    fs::remove_all(root); fs::create_directories(root/"ISS");
    std::ofstream(root/"ISS"/"Station.msh") << "asset";
    ResourceResolver resources(root);
    require(resources.FileCount() == 1, "Resource index omitted a file");
    require(resources.Resolve("iss\\STATION.MSH") == fs::canonical(root)/"ISS"/"Station.msh", "Case/separator lookup failed");
    require(resources.Contains("./Iss//Station.msh"), "Normalized lookup failed");
    for (const auto* invalid : {"../Station.msh", "ISS/../../x", "/ISS/x", "C:\\ISS\\x", "\\\\server\\x", ""})
        rejects([&] { resources.Resolve(invalid); });
    rejects([&] { resources.Resolve("missing.msh"); });
    rejects([&] { ResourceResolver missing(root/"absent"); });
#ifndef _WIN32
    fs::create_directory(root/"iss");
    rejects([&] { ResourceResolver ambiguous(root); });
    fs::remove(root/"iss");
    fs::create_symlink("Station.msh", root/"ISS"/"Alias.msh");
    rejects([&] { ResourceResolver symlink(root); });
#endif
    fs::remove_all(root);
}

void meshTests(const fs::path& root)
{
    ResourceResolver resources(root);
    auto pb = [&] { std::ifstream stream(resources.Resolve("SHUTTLEPB.MSH")); return LoadMeshData(stream); }();
    require(pb.groups.size() == 7 && pb.materials.size() == 2 && pb.textures.size() == 2,
        "Stock ShuttlePB identity changed");
    require(pb.groups[0].vertices.size() == 56 && pb.groups[0].indices.size() == 156,
        "Stock mesh group ordering changed");
    const std::string triangle = "MSHX1\nGROUPS 1\nNONORMAL\nTEXWRAP UV\nFLAG 80000001\nZBIAS 2\nGEOM 3 1\n0 0 0 0 0\n1 0 0 1 0\n0 1 0 0 1\n0 1 2\n";
    std::istringstream input(triangle);
    auto cpu = LoadMeshData(input);
    auto& g = cpu.groups.at(0);
    require(g.userFlags == 0x80000001u && g.zBias == 2 && g.flags == 3, "Mesh flags lost");
    require(g.material == std::uint32_t(-2) && g.texture == std::uint32_t(-2), "Inheritance lost");
    require(g.vertices[0].nz == 1 && g.vertices[1].nz == 1 && g.vertices[2].nz == 1, "Normals changed");
    require(g.vertices[1].tu == 1 && g.vertices[2].tv == 1, "UVs changed");
    for (const auto& bad : {std::string("not a mesh"), triangle.substr(0, triangle.size()-4),
        std::string("MSHX1\nGROUPS 1\nGEOM -3 1\n")}) {
        rejects([&] { std::istringstream stream(bad); LoadMeshData(stream); });
    }
    for (const char* indices : {"65536 1 2", "-65536 1 2", "4294967296 1 2", "-1 1 2", "0 1 3",
        "9999999999999999999999999999999999 1 2", "+-0 1 2"}) {
        const auto bad = triangle.substr(0, triangle.rfind("0 1 2\n")) + indices + '\n';
        rejects([&] { std::istringstream stream(bad); LoadMeshData(stream); });
    }
    std::istringstream signedIndices(triangle.substr(0, triangle.rfind("0 1 2\n")) + "+0 +1 +2\n");
    require(LoadMeshData(signedIndices).groups[0].indices == g.indices,"Valid signed index syntax changed");
    for (const auto& counts : {std::pair<const char*,const char*>{"GROUPS 1","GROUPS 4294967297"},
        {"GEOM 3 1","GEOM 4294967299 1"},{"GEOM 3 1","GEOM 3 4294967297"}}) {
        auto bad=triangle;bad.replace(bad.find(counts.first),std::strlen(counts.first),counts.second);
        rejects([&] { std::istringstream stream(bad); LoadMeshData(stream); });
    }
    for (const char* counts : {"MATERIALS 4294967296\nTEXTURES 0\n","MATERIALS 0\nTEXTURES 4294967296\n"}) {
        rejects([&] { std::istringstream stream(triangle+counts); LoadMeshData(stream); });
    }
    std::size_t count = 0;
    for (const auto& path : fs::recursive_directory_iterator(root)) {
        if (path.path().extension() != ".msh") continue;
        std::ifstream stream(path.path());
        if (fs::file_size(path.path()) == 0) {
            require(path.path().filename() == "Hyperion.msh", "Unexpected empty stock mesh");
            rejects([&] { LoadMeshData(stream); });
            continue; // pinned upstream empty placeholder; never substitute geometry
        }
        MeshData mesh;
        try { mesh = LoadMeshData(stream); }
        catch (const std::exception& error) { throw std::runtime_error(path.path().string()+": "+error.what()); }
        for (const auto& group : mesh.groups)
            for (auto index : group.indices) require(index < group.vertices.size(), "Invalid stock group index");
        ++count;
    }
    require(count > 20, "Stock mesh test corpus missing");
    std::cout << "Read " << count << " original stock meshes through the shared production parser\n";
}

void bodyTests(const fs::path& temporary)
{
    BindBodyServices(nullptr);
    rejects([] { Body unbound; });
    struct Environment final : BodyServices {
        ResourceResolver resources;
        bool updating = false;
        int sizeChanges = 0, visualEvents = 0, statuses = 0;
        explicit Environment(const fs::path& root) : resources(root) {}
        bool IsUpdating() const override { return updating; }
        fs::path ConfigPath(const char* name) override { return resources.Resolve(std::string(name)+".cfg"); }
        void LoadStatus(const char*, int line) override { require(line == 1, "Wrong load-status order"); ++statuses; }
        void SizeChanged(Body*) override { ++sizeChanges; }
        void VisualEvent(Body*, BodyVisual visual, BodyParameter message, BodyContent content) override
        {
            require(visual == this && message == 7 && content == 9, "Visual notification identity changed");
            ++visualEvents;
        }
        void CheckUpdateState(bool valid) override { require(valid, "Body update state is unavailable"); }
    };
    const auto root = temporary/"body-fixture";
    fs::create_directories(root);
    std::ofstream(root/"Body.cfg") << "Name = ActualBody\r\nMass = 5.972e24\r\nSize = 6371000\r\n"
        "AlbedoRGB = 0.2 0.3 0.4\r\nInitPos = 1 2 3\r\nInitVel = 4 5 6\r\n";
    Environment environment(root);
    struct Binding {
        BodyServices* previous;
        explicit Binding(BodyServices* services) : previous(BindBodyServices(services)) {}
        ~Binding() { BindBodyServices(previous); }
    } binding(&environment);
    char name[] = "BODY";
    Body body(name);
    require(std::string(body.Name()) == "ActualBody" && body.Mass() == 5.972e24 && body.Size() == 6371000,
        "Production Body configuration changed");
    require(body.GPos().x == 1 && body.GVel().z == 6 && body.s0 == body.s1, "Body initial state changed");
    require(environment.statuses == 1, "Production config load was not observed");
    const auto* original = body.s0;
    body.BeginStateUpdate();
    require(body.s0 == original && body.s1 != original, "Body published unfinished state");
    body.RPlace(Vector(7,8,9), Vector(10,11,12));
    body.s1->R = IMatrix();
    require(body.GPos().x == 1, "Body changed its current state before finalization");
    body.EndStateUpdate();
    require(body.s0 == body.s1 && body.GPos().x == 7 && body.GVel().z == 12, "Body finalization order changed");
    Vector global;
    body.LocalToGlobal(Vector(1,2,3), global);
    require(global.x == 8 && global.y == 10 && global.z == 12, "Production frame transform changed");
    body.SetSize(4); require(environment.sizeChanges == 1, "Size notification missing");
    body.BroadcastVisMsg(7,9); require(environment.visualEvents == 0, "Unregistered visual received event");
    body.RegisterVisual(&environment); body.BroadcastVisMsg(7,9);
    require(environment.visualEvents == 1, "Registered visual notification missing");
    body.UnregisterVisual();
    environment.updating = true;
    Body createdDuringUpdate(1,2);
    require(createdDuringUpdate.s0 != createdDuringUpdate.s1, "Creation during a state update changed");
    char missing[] = "missing";
    rejects([&] { Body absent(missing); });
    fs::remove_all(root);
}

int main(int argc, char** argv)
{
    try {
        require(argc >= 2, "Missing test selection");
        const std::string suite = argv[1];
        if (suite == "session") sessionTests();
        else if (suite == "resources" && argc == 3) resourceTests(argv[2]);
        else if (suite == "meshes" && argc == 3) meshTests(argv[2]);
        else if (suite == "bodies" && argc == 3) bodyTests(argv[2]);
        else throw std::runtime_error("Invalid test selection");
        return 0;
    } catch (const std::exception& error) { std::cerr << error.what() << '\n'; return 1; }
}
