#include "RuntimeLibrary.h"

#include <QCoreApplication>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QJsonDocument>
#include <QJsonObject>
#include <QSet>
#include <QSettings>
#include <QStandardPaths>
#include <algorithm>

namespace {
bool isCheckout(const QDir &dir)
{
    return dir.exists("Src/Orbiter") && dir.exists("Orbitersdk");
}

QString parentCheckout(QDir dir)
{
    do {
        if (isCheckout(dir))
            return dir.absolutePath();
    } while (dir.cdUp());
    return {};
}

QSettings librarySettings()
{
    return QSettings(QSettings::defaultFormat(), QSettings::UserScope,
                     QCoreApplication::organizationName(), "Orbiter Project Launcher");
}
}

std::optional<OrbiterRuntime> runtimeAt(const QString &path, bool explicitProfile)
{
    const QFileInfo file(path);
    if (!file.isFile())
        return {};
#ifdef Q_OS_WIN
    if (file.fileName().compare("Orbiter.exe", Qt::CaseInsensitive) == 0)
        return OrbiterRuntime{"Classic Windows", file.canonicalFilePath()};
#endif
    if (file.suffix().compare("json", Qt::CaseInsensitive) != 0 || file.size() > 1024 * 1024)
        return {};
    QFile input(path);
    if (!input.open(QIODevice::ReadOnly))
        return {};
    const auto json = QJsonDocument::fromJson(input.readAll()).object();
    const QDir dir = file.absoluteDir();
    const QFileInfo engine(dir.absoluteFilePath(json.value("executable").toString()));
    if (!engine.isFile() || !engine.isExecutable())
        return {};
    const auto mode = json.value("mode").toString();
#ifdef Q_OS_WIN
    if (mode == "windows" && engine.fileName().compare("Orbiter.exe", Qt::CaseInsensitive) == 0)
        return OrbiterRuntime{"Classic Windows", file.canonicalFilePath()};
#endif
    if (mode != "native")
        return {};
    if (!explicitProfile) {
        // Mission bundles carry their own engine/run-orbiter adapter. Only a
        // native simulator installation is eligible for automatic discovery.
        if (engine.completeBaseName().compare("orbiter-production", Qt::CaseInsensitive) != 0)
            return {};
        for (const auto &field : {"assets", "data", "planets", "modules"}) {
            const auto location = json.value(field).toString();
            if (location.isEmpty() || !QFileInfo(dir.filePath(location)).isDir())
                return {};
        }
        if (!QFileInfo(dir.filePath(json.value("assets").toString() + "/Scenarios")).isDir() ||
            !QFileInfo(dir.filePath(json.value("config").toString())).isFile())
            return {};
    }
    const auto graphics = json.value("graphics").toString("opengl");
    QString name;
    if (graphics == "opengl")
        name = "OpenGL";
    else if (graphics == "vulkan")
        name = "Vulkan";
    else if (graphics == "d3d9")
        name = "D3D9";
    else
        return {};
    return OrbiterRuntime{name, file.canonicalFilePath()};
}

QVector<OrbiterRuntime> findOrbiterRuntimes(const QStringList &locations)
{
    QVector<OrbiterRuntime> found;
    QSet<QString> families, visited;
    const auto collect = [&](const QString &path) {
        if (const auto runtime = runtimeAt(path); runtime && !families.contains(runtime->name)) {
            families.insert(runtime->name);
            found.append(*runtime);
        }
    };
    const auto inspect = [&](const QDir &dir) {
        for (const auto &file : {"Launchpad profile.json", "linux-profile.json", "vulkan.json",
                                 "d3d9.json", "orbiter-profile.json"})
            collect(dir.filePath(file));
#ifdef Q_OS_WIN
        collect(dir.filePath("runtime/Orbiter.exe"));
        collect(dir.filePath("Orbiter.exe"));
#endif
    };
    for (const auto &location : locations) {
        const QFileInfo entry(location);
        const auto path = entry.canonicalFilePath();
        if (path.isEmpty() || visited.contains(path))
            continue;
        visited.insert(path);
        if (entry.isFile()) {
            collect(path);
            continue;
        }
        const QDir dir(path);
        if (isCheckout(dir)) {
            for (const auto &folder : {"out/qt-launchpad", "out/vulkan-flight", "out/d3d9-dxvk"})
                inspect(QDir(dir.filePath(folder)));
        } else {
            inspect(dir);
            for (const auto &child : dir.entryInfoList(QDir::Dirs | QDir::NoDotAndDotDot))
                inspect(QDir(child.absoluteFilePath()));
        }
    }
    const QStringList order{"OpenGL", "Vulkan", "D3D9", "Classic Windows"};
    std::sort(found.begin(), found.end(), [&](const auto &a, const auto &b) {
        return order.indexOf(a.name) < order.indexOf(b.name);
    });
    return found;
}

QStringList standardRuntimeLocations()
{
    const QDir home = QDir::home();
    auto locations = qEnvironmentVariable("ORBITER_RUNTIME_PATH").split(QDir::listSeparator(), Qt::SkipEmptyParts);
    const QSettings launchpad("Orbiter", "Orbiter Launchpad");
    const auto last = launchpad.value("simulator/profile").toString();
    if (!last.isEmpty())
        locations << last << parentCheckout(QFileInfo(last).absoluteDir());
    locations << parentCheckout(QDir::current()) << home.filePath("Orbiter") << home.filePath("Games")
              << home.filePath("Applications") << QStandardPaths::writableLocation(QStandardPaths::DownloadLocation);
    for (const auto &data : QStandardPaths::standardLocations(QStandardPaths::GenericDataLocation))
        locations << QDir(data).filePath("orbiter/runtimes");
#ifdef Q_OS_WIN
    for (const auto &name : {"ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA"}) {
        const QString value = qEnvironmentVariable(name);
        if (!value.isEmpty())
            locations << value << QDir(value).filePath("Orbiter");
    }
#elif defined(Q_OS_MACOS)
    locations << "/Applications" << "/Applications/Orbiter";
#else
    locations << "/opt" << "/opt/orbiter" << home.filePath(".local/opt");
#endif
    locations.removeAll(QString());
    locations.removeDuplicates();
    return locations;
}

QStringList registeredLocations()
{
    return librarySettings().value("library/locations").toStringList();
}

void rememberLocation(const QString &location)
{
    auto locations = registeredLocations();
    const QString path = QFileInfo(location).canonicalFilePath();
    if (!path.isEmpty()) {
        locations.removeAll(path);
        locations.prepend(path);
        librarySettings().setValue("library/locations", locations);
    }
}

void forgetLocation(const QString &location)
{
    auto locations = registeredLocations();
    locations.removeAll(location);
    librarySettings().setValue("library/locations", locations);
}

QString lastProjectRuntime()
{
    return librarySettings().value("library/selected").toString();
}

void rememberProjectRuntime(const QString &path)
{
    librarySettings().setValue("library/selected", path);
}
