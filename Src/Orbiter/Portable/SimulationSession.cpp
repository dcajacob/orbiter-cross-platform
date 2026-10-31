// Licensed under the MIT License.
#include "SimulationSession.h"
#include "ConfigFile.h"
#include "PhysicsCore.h"
#include <algorithm>
#include <cctype>
#include <cmath>
#include <fstream>
#include <map>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace orbiter { namespace portable {
namespace {
using Fields = std::map<std::string,std::string>;
void Require(bool condition, const std::string &message) {
    if (!condition) throw std::runtime_error(message);
}
std::string Lower(std::string text) {
    for (char &c : text) c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
    return text;
}
std::string Clean(std::string line) {
    Require(line.size() < 512, "scenario/configuration line exceeds supported length");
    line.push_back('\0');
    return trim_string(&line[0]);
}
std::vector<std::string> Words(const std::string &text) {
    std::istringstream stream(text);
    stream.imbue(std::locale::classic());
    std::vector<std::string> words;
    for (std::string word; stream >> word;) words.push_back(word);
    return words;
}
bool Identifier(const std::string &name) {
    return !name.empty() && std::all_of(name.begin(),name.end(),[](unsigned char c) {
        return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') ||
            (c >= '0' && c <= '9') || c == '_' || c == '-';
    });
}
std::vector<double> Numbers(const std::string &text, std::size_t count) {
    const auto words = Words(text);
    Require(words.size() == count, "incorrect number of numeric fields: " + text);
    std::vector<double> values;
    for (const auto &word : words) {
        std::istringstream stream(word);
        stream.imbue(std::locale::classic());
        double value;
        Require(bool(stream >> value) && std::isfinite(value), "invalid finite number: " + word);
        stream >> std::ws;
        Require(stream.eof(), "invalid numeric suffix: " + word);
        values.push_back(value);
    }
    return values;
}
double Number(const std::string &text) { return Numbers(text,1)[0]; }
Vector Triple(const std::string &text) {
    const auto v = Numbers(text,3);
    return Vector(v[0],v[1],v[2]);
}
bool Boolean(const std::string &text) {
    const auto value = Lower(text);
    Require(value == "true" || value == "false", "invalid boolean: " + text);
    return value == "true";
}
const std::string &Field(const Fields &fields, const std::string &key) {
    auto found = fields.find(key);
    Require(found != fields.end(), "missing required field: " + key);
    return found->second;
}
void Insert(Fields &fields, const std::string &key, const std::string &value) {
    Require(fields.emplace(Lower(key),value).second, "duplicate field: " + key);
}
Fields Configuration(const std::filesystem::path &path, const std::set<std::string> &allowed) {
    std::ifstream file(path);
    Require(bool(file), "cannot open configuration: " + path.string());
    std::set<std::string> keys;
    for (std::string line; std::getline(file,line);) {
        line = Clean(line);
        if (line.empty()) continue;
        const auto equals = line.find('=');
        Require(equals != std::string::npos, "configuration requires key = value: " + path.string());
        const auto key = Lower(Clean(line.substr(0,equals)));
        Require(allowed.count(key) != 0, "unsupported configuration field " + key + " in " + path.string());
        Require(keys.insert(key).second, "duplicate configuration field: " + key);
    }
    Require(file.eof(), "cannot read configuration: " + path.string());
    Fields result;
    for (const auto &key : keys) {
        char value[512];
        Require(GetItemString(file,key.c_str(),value), "missing configuration value: " + key);
        result.emplace(key,value);
    }
    return result;
}
std::filesystem::path Profile(const std::filesystem::path &root) {
    const auto fields = Configuration(root / "Orbiter.cfg", {
        "configdir","scenariodir","startpaused","demomode","backgroundimage",
        "distributedvesselmass","nonsphericalgravitysources","radiationpressure",
        "atmosphericwind","basecollision","vesselcollision","stabiliseorbits",
        "propstages","propstage0","propsubsampling","fixedstep","shutdownmode","saveexitscreen"});
    for (const char *key : {"startpaused","demomode","backgroundimage","distributedvesselmass",
            "nonsphericalgravitysources","radiationpressure","atmosphericwind","basecollision",
            "vesselcollision","stabiliseorbits","saveexitscreen"}) {
        Require(!Boolean(Field(fields,key)), std::string("unsupported enabled feature: ") + key);
    }
    Require(Number(Field(fields,"propstages")) == 1 && Number(Field(fields,"propsubsampling")) == 1,
        "portable session requires one RK4 stage and one substep");
    const auto mode = Numbers(Field(fields,"propstage0"),3);
    Require(mode[0] == 1 && mode[1] > 0 && mode[2] > 0, "portable session requires RK4 (mode 1)");
    Require(Number(Field(fields,"fixedstep")) > 0, "configuration fixed step must be positive");
    Require(Number(Field(fields,"shutdownmode")) == 0, "portable session requires normal resource cleanup");
    auto config = Field(fields,"configdir");
    std::replace(config.begin(),config.end(),'\\','/');
    const std::filesystem::path relative(config);
    Require(!relative.is_absolute() && config.find(':') == std::string::npos,
        "ConfigDir must be relative to the scenario bundle");
    for (const auto &part : relative) Require(part != "..", "ConfigDir cannot leave the scenario bundle");
    return root / relative;
}
struct Scenario {
    std::string system, focus, name, vesselClass, primary;
    double mjd = 0;
    Vector position, velocity, orientation, omega;
};
Scenario ReadScenario(const std::filesystem::path &path) {
    std::ifstream file(path);
    Require(bool(file), "cannot open scenario: " + path.string());
    std::vector<std::string> lines;
    for (std::string line; std::getline(file,line);) {
        line = Clean(line);
        if (!line.empty()) lines.push_back(line);
    }
    Require(file.eof(), "cannot read scenario: " + path.string());
    Fields environment, focus, vessel;
    std::set<std::string> blocks;
    Scenario result;
    for (std::size_t i = 0; i < lines.size();) {
        const auto block = Lower(lines[i++]);
        Require(blocks.insert(block).second, "duplicate scenario block: " + block);
        Require(block == "begin_environment" || block == "begin_focus" || block == "begin_ships",
            "unsupported scenario block: " + block);
        const std::string end = block == "begin_environment" ? "end_environment" :
            block == "begin_focus" ? "end_focus" : "end_ships";
        if (block == "begin_ships") {
            Require(i < lines.size(), "missing vessel");
            const auto colon = lines[i].find(':');
            Require(colon != std::string::npos, "vessel requires name:class");
            result.name = lines[i].substr(0,colon);
            result.vesselClass = lines[i++].substr(colon+1);
            Require(Identifier(result.name) && Identifier(result.vesselClass), "unsupported vessel identifier");
        }
        bool vesselEnd = false;
        for (; i < lines.size() && Lower(lines[i]) != end; ++i) {
            if (block == "begin_ships" && Lower(lines[i]) == "end") {
                Require(!vesselEnd, "only one vessel is supported");
                vesselEnd = true;
                continue;
            }
            Require(!vesselEnd, "only one vessel is supported");
            const auto space = lines[i].find_first_of(" \t");
            Require(space != std::string::npos, "malformed scenario field: " + lines[i]);
            const auto key = Lower(lines[i].substr(0,space));
            const auto value = Clean(lines[i].substr(space+1));
            if (block == "begin_environment") {
                Require(key == "system" || key == "date", "unsupported environment field: " + key);
                Insert(environment,key,value);
            } else if (block == "begin_focus") {
                Require(key == "ship", "unsupported focus field: " + key);
                Insert(focus,key,value);
            } else {
                Require(key == "status" || key == "rpos" || key == "rvel" || key == "arot" || key == "vrot",
                    "unsupported vessel field: " + key);
                Insert(vessel,key,value);
            }
        }
        Require(i < lines.size(), "unterminated scenario block: " + block);
        Require(block != "begin_ships" || vesselEnd, "missing vessel END");
        ++i;
    }
    result.system = Field(environment,"system");
    Require(Identifier(result.system), "unsupported system identifier");
    const auto date = Words(Field(environment,"date"));
    Require(date.size() == 2 && Lower(date[0]) == "mjd", "scenario Date requires MJD");
    result.mjd = Number(date[1]);
    Require(!result.name.empty(), "scenario requires exactly one vessel");
    if (!focus.empty()) Require(Field(focus,"ship") == result.name, "focus vessel not found");
    const auto status = Words(Field(vessel,"status"));
    Require(status.size() == 2 && Lower(status[0]) == "orbiting", "only an orbiting vessel is supported");
    result.primary = status[1];
    result.position = Triple(Field(vessel,"rpos"));
    result.velocity = Triple(Field(vessel,"rvel"));
    if (vessel.count("arot")) result.orientation = Triple(vessel.at("arot")) * _RAD_;
    if (vessel.count("vrot")) result.omega = Triple(vessel.at("vrot")) * _RAD_;
    Require(result.omega.length() <= 100*Pi, "initial angular velocity exceeds engine limit");
    return result;
}
}

SimulationSession SimulationSession::Load(const std::filesystem::path &scenario, double fixedStep) {
    Require(std::isfinite(fixedStep) && fixedStep > 0 && std::isfinite(1/fixedStep),
        "fixed step must be finite, positive and have a finite reciprocal");
    const auto initial = ReadScenario(scenario);
    const auto config = Profile(scenario.parent_path());
    const auto system = Configuration(config / (initial.system+".cfg"), {"name","star1"});
    const auto primaryFile = Field(system,"star1");
    Require(Identifier(primaryFile), "unsupported primary identifier");
    const auto primary = Configuration(config / (primaryFile+".cfg"),
        {"name","mass","size","initpos","initvel","sidrotperiod"});
    Require(Field(primary,"name") == initial.primary, "scenario reference primary not found");
    Require(Triple(Field(primary,"initvel")).length2() == 0, "moving primaries are unsupported");
    Require(Number(Field(primary,"sidrotperiod")) > 0, "invalid primary rotation period");
    const auto vessel = Configuration(config / "Vessels" / (initial.vesselClass+".cfg"),
        {"mass","size","inertia","crosssections","enablefocus","gravitygradientdamping"});
    Require(Number(Field(vessel,"mass")) > 0 && Number(Field(vessel,"size")) > 0,
        "vessel mass and size must be positive");
    Require(Triple(Field(vessel,"crosssections")).length2() == 0, "aerodynamic vessels are unsupported");
    Require(Number(Field(vessel,"gravitygradientdamping")) == 0, "gravity-gradient damping is unsupported");
    (void)Boolean(Field(vessel,"enablefocus"));
    SimulationSession session;
    session.inputs = {scenario,scenario.parent_path()/"Orbiter.cfg",config/(initial.system+".cfg"),
        config/(primaryFile+".cfg"),config/"Vessels"/(initial.vesselClass+".cfg")};
    session.step = fixedStep;
    session.primaryMass = Number(Field(primary,"mass"));
    session.primaryRadius = Number(Field(primary,"size"));
    Require(session.primaryMass > 0 && session.primaryRadius > 0, "primary mass and radius must be positive");
    session.primaryPosition = Triple(Field(primary,"initpos"));
    session.inertia = Triple(Field(vessel,"inertia"));
    Require(session.inertia.x > 0 && session.inertia.y > 0 && session.inertia.z > 0,
        "principal inertia must be positive");
    session.state.pos = session.positionBase = initial.position + session.primaryPosition;
    session.state.vel = session.velocityBase = initial.velocity + Triple(Field(primary,"initvel"));
    session.state.R.Set(initial.orientation);
    session.state.Q.Set(session.state.R);
    session.state.omega = initial.omega;
    session.acceleration = physics::PointMassAcceleration(session.primaryPosition-session.state.pos,session.primaryMass);
    session.angularAcceleration = physics::EulerAcceleration(session.inertia,Vector(0,0,0),session.state.omega);
    session.time.Reset(initial.mjd);
    session.time.SetFixedStep(fixedStep);
    session.ValidateState();
    return session;
}

void SimulationSession::ValidateState() const {
    for (double x : state.pos.data) Require(std::isfinite(x), "nonfinite simulation position");
    for (double x : state.vel.data) Require(std::isfinite(x), "nonfinite simulation velocity");
    for (double x : state.Q.data) Require(std::isfinite(x), "nonfinite simulation orientation");
    for (double x : state.omega.data) Require(std::isfinite(x), "nonfinite simulation angular velocity");
    Require(std::abs(state.Q.norm()-1) <= 1e-12, "non-unit simulation orientation");
    const double radius = (state.pos-primaryPosition).length();
    Require(std::isfinite(radius) && std::isfinite(state.vel.length()), "nonfinite simulation magnitude");
    Require(std::isfinite(acceleration.length()) && std::isfinite(angularAcceleration.length()),
        "nonfinite simulation acceleration");
    Require(radius > primaryRadius, "surface contact is unsupported");
    Require(std::isfinite(time.SimT0) && std::isfinite(time.MJD0), "nonfinite simulation time");
}

void SimulationSession::Step() {
    time.BeginStep(step,true);
    StateVectors next;
    next.Set(state);
    physics::AdvanceRK4(next,acceleration,angularAcceleration,velocityDelta,positionDelta,step,1,0,
        [this](Vector &a, Vector &tau, const StateVectors &s, double, double) {
            a = physics::PointMassAcceleration(primaryPosition-s.pos,primaryMass);
            tau.Set(0,0,0);
        },
        [this](const Vector &tau, const Vector &omega) { return physics::EulerAcceleration(inertia,tau,omega); });
    physics::FinalizeStage(next,positionBase,velocityBase,positionDelta,velocityDelta);
    acceleration = physics::PointMassAcceleration(primaryPosition-next.pos,primaryMass);
    angularAcceleration = physics::EulerAcceleration(inertia,Vector(0,0,0),next.omega);
    physics::FlushIncrements(positionBase,velocityBase,positionDelta,velocityDelta,flushCounter);
    state.Set(next);
    time.EndStep(true);
    ValidateState();
}

PhysicsTraceSample SimulationSession::ReadState() const {
    const Vector r = state.pos-primaryPosition;
    return {time.FrameCount(),time.SimT0,time.MJD0,{r.x,r.y,r.z},
        {state.vel.x,state.vel.y,state.vel.z},{state.Q.qvx,state.Q.qvy,state.Q.qvz,state.Q.qs},
        {state.omega.x,state.omega.y,state.omega.z}};
}
bool SimulationSession::IsInputFile(const std::filesystem::path &path) const {
    if (!std::filesystem::exists(path)) return false;
    for (const auto &input : inputs) if (std::filesystem::equivalent(path,input)) return true;
    return false;
}
}}
