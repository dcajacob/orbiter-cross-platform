// Licensed under the MIT License
#pragma once
#include <QCryptographicHash>
#include <QDirIterator>
#include <QFile>
#include <QFileInfo>
#include <QLockFile>
#include <QMap>
#include <QSaveFile>
#include <QStandardPaths>
#include <stdexcept>

namespace installed_profile {
inline void makeDirectory(const QString &path) {
    if (!QDir().mkpath(path)) throw std::runtime_error(("Cannot create " + path).toStdString());
}
inline void seedFile(const QString &src, const QString &dst) {
    if (QFileInfo::exists(dst) || !QFileInfo(src).isFile()) return;
    makeDirectory(QFileInfo(dst).absolutePath());
    QFile in(src);
    QSaveFile out(dst);
    if (!in.open(QIODevice::ReadOnly) || !out.open(QIODevice::WriteOnly))
        throw std::runtime_error(("Cannot initialize " + dst).toStdString());
    while (!in.atEnd()) {
        auto data = in.read(65536);
        if (in.error()!=QFileDevice::NoError || out.write(data)!=data.size())
            throw std::runtime_error(("Cannot copy " + src).toStdString());
    }
    if (!out.commit()) throw std::runtime_error(out.errorString().toStdString());
}
inline QString macState(const QDir &install) {
    const auto key = QCryptographicHash::hash(install.canonicalPath().toUtf8(), QCryptographicHash::Sha256).toHex();
    return QDir(QStandardPaths::writableLocation(QStandardPaths::GenericDataLocation))
            .filePath("Orbiter/Installations/" + key);
}
inline void prepareMac(const QDir &install, QString &config, QString &keymap, QString &saves,
                       QMap<QString,QString> *overrides) {
    const QDir personal(macState(install));
    makeDirectory(personal.absolutePath());
    QLockFile lock(personal.filePath("setup.lock"));
    if (!lock.tryLock(30000)) throw std::runtime_error("Cannot lock Orbiter user profile");
    const auto oldConfig = config, oldSaves = saves;
    config = personal.filePath("Orbiter.cfg");
    seedFile(oldConfig,config);
    if (!keymap.isEmpty()) {
        const auto original = keymap;
        keymap = personal.filePath("Keymap.cfg");
        seedFile(original,keymap);
    }
    saves = personal.filePath("Scenarios");
    makeDirectory(saves);
    if (!oldSaves.isEmpty()) {
        QDirIterator files(oldSaves, {"*.scn"}, QDir::Files|QDir::NoSymLinks, QDirIterator::Subdirectories);
        while (files.hasNext()) { const auto path=files.next(); seedFile(path,QDir(saves).filePath(QDir(oldSaves).relativeFilePath(path))); }
    }
    if (overrides) {
        QMap<QString,QString> resolved;
        for (auto it = overrides->cbegin(); it != overrides->cend(); ++it) {
            auto dest = config;
            if (it.value()!=oldConfig) {
                const auto key=QCryptographicHash::hash(it.value().toUtf8(),QCryptographicHash::Sha256).toHex();
                dest=personal.filePath("configs/"+key+".cfg");
                seedFile(it.value(),dest);
            }
            const auto relative=QDir(oldSaves).relativeFilePath(it.key());
            const bool personalScene=!oldSaves.isEmpty() && !relative.startsWith("../") && !QDir::isAbsolutePath(relative);
            resolved.insert(personalScene ? QDir(saves).filePath(relative) : it.key(),dest);
        }
        *overrides = resolved;
    }
}
}
