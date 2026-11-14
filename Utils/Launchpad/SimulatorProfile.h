#pragma once

#include <QDir>
#include <QProcessEnvironment>
#include <QString>
#include <QStringList>

struct SimulatorProfile {
    QString executable;
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
    QProcessEnvironment environment;
    bool native = false;
    bool configured = false;

    static SimulatorProfile load(const QString &profilePath);
    static SimulatorProfile fromWindowsExecutable(const QString &path);
    QString validationError() const;
    QStringList arguments(const QString &scenario, bool startPaused) const;
};
