#pragma once

#include <QDir>
#include <QMap>
#include <QProcessEnvironment>
#include <QString>
#include <QStringList>

struct SimulatorProfile {
    QString executable;
    QString graphics;
    QString scenarioRoot;
    QString workingDirectory;
    QString assets;
    QString data;
    QString modules;
    QString planets;
    QString config;
    QString keymap;
    QString xrsoundAssets;
    QString saveRoot;
    QString helpRoot;
    QMap<QString, QString> scenarioConfigs;
    QProcessEnvironment environment;
    bool native = false;
    bool configured = false;

    static SimulatorProfile load(const QString &profilePath);
    static SimulatorProfile fromWindowsExecutable(const QString &path);
    SimulatorProfile forScenario(const QString &path) const;
    QString validationError() const;
    bool launchWithSound() const;
    QString setLaunchWithSound(bool enabled) const;
    QStringList arguments(const QString &scenario, bool startPaused) const;
private:
    QString sharedSoundConfig;
};
