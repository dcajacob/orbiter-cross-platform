#pragma once

#include <QStringList>
#include <QVector>
#include <optional>

struct OrbiterRuntime {
    QString name;
    // Path to the simulator profile or to a classic Windows executable.
    QString path;
};

std::optional<OrbiterRuntime> runtimeAt(const QString &path, bool explicitProfile = false);
QVector<OrbiterRuntime> findOrbiterRuntimes(const QStringList &locations);
QStringList standardRuntimeLocations();
QStringList registeredLocations();
void rememberLocation(const QString &location);
void forgetLocation(const QString &location);
QString lastProjectRuntime();
void rememberProjectRuntime(const QString &path);
