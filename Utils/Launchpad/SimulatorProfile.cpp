#include "SimulatorProfile.h"

#include <QFile>
#include <QFileInfo>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QRegularExpression>
#include <QSettings>
#include <QStandardPaths>
#include <QUrl>

#include <stdexcept>

namespace {
QString absolutePath(const QDir &base, const QString &path)
{
    return path.isEmpty() ? QString() : QDir::cleanPath(base.absoluteFilePath(path));
}

QString soundPreferenceKey(const QString &config)
{
    const auto path = QFileInfo(config).canonicalFilePath();
    return "simulator/modules/" + QUrl::toPercentEncoding(path) + "/xrsound";
}
}

SimulatorProfile SimulatorProfile::load(const QString &profilePath)
{
    QFile file(profilePath);
    if (!file.open(QIODevice::ReadOnly))
        throw std::runtime_error(file.errorString().toStdString());
    QJsonParseError error;
    const auto document = QJsonDocument::fromJson(file.readAll(), &error);
    if (!document.isObject())
        throw std::runtime_error(error.error == QJsonParseError::NoError
            ? "Expected a simulator profile object" : error.errorString().toStdString());
    const auto json = document.object();
    const QDir base = QFileInfo(file).absoluteDir();
    const auto path = [&](const QString &key) { return absolutePath(base, json.value(key).toString()); };
    const auto mode = json.value("mode").toString();
    if (mode == "windows") {
        auto profile = fromWindowsExecutable(path("executable"));
        if (!path("help").isEmpty())
            profile.helpRoot = path("help");
        return profile;
    }
    if (mode != "native")
        throw std::runtime_error("Profile mode must be native or windows");

    SimulatorProfile profile;
    profile.native = true;
    profile.configured = true;
    profile.executable = path("executable");
    profile.assets = path("assets");
    profile.data = path("data");
    profile.modules = path("modules");
    profile.planets = path("planets");
    profile.config = path("config");
    profile.keymap = path("keymap");
    profile.xrsoundAssets = path("xrsoundAssets");
    profile.helpRoot = path("help");
    profile.scenarioRoot = QDir(profile.assets).absoluteFilePath("Scenarios");
    profile.saveRoot = path("saves");
    if (profile.saveRoot.isEmpty())
        profile.saveRoot = QDir(QStandardPaths::writableLocation(QStandardPaths::AppDataLocation))
                               .absoluteFilePath("Scenarios");
    profile.workingDirectory = QFileInfo(profile.saveRoot).absolutePath();
    profile.environment = QProcessEnvironment::systemEnvironment();
    for (const auto &name : json.value("unsetEnvironment").toArray())
        profile.environment.remove(name.toString());
    const auto overrides = json.value("environment").toObject();
    for (auto it = overrides.begin(); it != overrides.end(); ++it)
        profile.environment.insert(it.key(), it.value().toString());
    return profile;
}

SimulatorProfile SimulatorProfile::fromWindowsExecutable(const QString &path)
{
    SimulatorProfile profile;
    profile.configured = true;
    profile.executable = path;
    profile.workingDirectory = QFileInfo(path).absolutePath();
    QDir root(profile.workingDirectory);
    QString scenarioDirectory = "Scenarios";
    profile.config = root.filePath("Orbiter.cfg");
    QFile config(profile.config);
    if (config.open(QIODevice::ReadOnly)) {
        const QRegularExpression pattern(R"(^\s*ScenarioDir\s*=\s*([^;\r\n]+))",
            QRegularExpression::MultilineOption | QRegularExpression::CaseInsensitiveOption);
        const auto match = pattern.match(QString::fromLocal8Bit(config.readAll()));
        if (match.hasMatch())
            scenarioDirectory = match.captured(1).trimmed();
    }
    profile.scenarioRoot = absolutePath(root, QDir::fromNativeSeparators(scenarioDirectory));
    profile.helpRoot = root.filePath("Html/Scenarios");
    profile.environment = QProcessEnvironment::systemEnvironment();
    return profile;
}

bool SimulatorProfile::launchWithSound() const
{
    return native && !xrsoundAssets.isEmpty() && QSettings().value(soundPreferenceKey(config), true).toBool();
}

QString SimulatorProfile::setLaunchWithSound(bool enabled) const
{
    QSettings settings;
    settings.setValue(soundPreferenceKey(config), enabled);
    settings.sync();
    return settings.status() == QSettings::NoError ? QString() : QObject::tr("Could not save the XRSound preference.");
}

QString SimulatorProfile::validationError() const
{
    if (!configured)
        return QObject::tr("Choose a simulator in Setup.");
#ifndef Q_OS_WIN
    if (!native)
        return QObject::tr("The Windows simulator can only launch on Windows.");
#endif
    if (!QFileInfo(executable).isFile() || !QFileInfo(executable).isExecutable())
        return QObject::tr("Simulator executable missing or unusable: %1").arg(executable);
    if (!QFileInfo(scenarioRoot).isDir())
        return QObject::tr("Scenarios folder missing: %1").arg(scenarioRoot);
    if (native) {
        for (const auto &directory : {assets, data, modules, planets}) {
            if (!QFileInfo(directory).isDir())
                return QObject::tr("Simulator data folder missing: %1").arg(directory);
        }
        if (!QFileInfo(config).isFile())
            return QObject::tr("Simulator configuration missing: %1").arg(config);
        if (!keymap.isEmpty() && !QFileInfo(keymap).isFile())
            return QObject::tr("Keyboard map missing: %1").arg(keymap);
        if (launchWithSound() && !QFileInfo(QDir(xrsoundAssets).filePath("XRSound/XRSound.cfg")).isFile())
            return QObject::tr("XRSound configuration missing in %1").arg(xrsoundAssets);
    }
    return {};
}

QStringList SimulatorProfile::arguments(const QString &scenario, bool startPaused) const
{
    if (!native) {
        QString name = QDir(scenarioRoot).relativeFilePath(scenario);
        name.chop(4); // Orbiter's Windows command line expects a name without .scn.
        return {"--scenariox=" + QDir::toNativeSeparators(name)};
    }

    QStringList result{"--assets", assets, "--data", data, "--modules", modules, "--planets", planets,
                       "--config", config, "--scenario", scenario,
                       "--save", QDir(saveRoot).filePath("Quicksave.scn")};
    if (!keymap.isEmpty())
        result << "--keymap" << keymap;
    if (launchWithSound())
        result << "--xrsound-assets" << xrsoundAssets;
    if (!startPaused)
        result << "--run";
    return result;
}
