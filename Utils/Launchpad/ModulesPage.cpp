#include "ModulesPage.h"
#include "SimulatorProfile.h"

#include <QFileInfo>
#include <QHeaderView>
#include <QLabel>
#include <QSet>
#include <QTreeWidget>
#include <QVBoxLayout>

#ifdef Q_OS_WIN
#include <qt_windows.h>
#endif

namespace {
// Config::FindLine and the END_MODULES check compare prefixes at column zero.
struct StartupBlock {
    explicit StartupBlock(const QStringList &lines) {
        for (int i = 0; i < lines.size(); ++i) {
            if (start < 0) {
                if (lines[i].startsWith("ACTIVE_MODULES", Qt::CaseInsensitive))
                    start = i;
            } else if (lines[i].startsWith("END_MODULES", Qt::CaseInsensitive)) {
                end = i;
                break;
            } else {
                const auto name = lines[i].section(';', 0, 0).trimmed();
                if (!name.isEmpty())
                    names.insert(name.toCaseFolded(), name);
            }
        }
    }
    int start = -1;
    int end = -1;
    QMap<QString, QString> names;
};

bool graphicsClient(const QString &name, const QString &file)
{
    if (name.compare("OGLClient", Qt::CaseInsensitive) == 0 ||
        name.compare("D3D9Client", Qt::CaseInsensitive) == 0)
        return true;
#ifdef Q_OS_WIN
    // Read the classic category resource without executing the plug-in.
    const HMODULE library = LoadLibraryExW(reinterpret_cast<LPCWSTR>(file.utf16()), nullptr, LOAD_LIBRARY_AS_DATAFILE);
    if (library) {
        wchar_t category[256];
        const int size = LoadStringW(library, 1001, category, 256);
        FreeLibrary(library);
        return QString::fromWCharArray(category, size) == "Graphics engines";
    }
#else
    Q_UNUSED(file);
#endif
    return false;
}
}

ModulesPage::ModulesPage(const SimulatorProfile &profile, const QString &config)
{
    setObjectName("modulesPage");
    auto *layout = new QVBoxLayout(this);
    list = new QTreeWidget;
    list->setObjectName("moduleList");
    list->setRootIsDecorated(false);
    list->setHeaderLabels({tr("Plug-in"), tr("Use in flight")});
    list->header()->setSectionResizeMode(0, QHeaderView::ResizeToContents);
    list->setMinimumWidth(370);
    layout->addWidget(list);

    const auto root = profile.native ? profile.modules : QDir(profile.workingDirectory).filePath("Modules");
    const QDir plugins(QDir(root).filePath("Plugin"));
    const StartupBlock block(config.split('\n'));
    auto remaining = block.names;
    auto row = [&](const QString &name, const QString &detail) {
        auto *item = new QTreeWidgetItem(list, {name, detail});
        item->setFlags(Qt::ItemIsEnabled | Qt::ItemIsSelectable);
        return item;
    };
    auto check = [](QTreeWidgetItem *item, bool checked) {
        item->setFlags(item->flags() | Qt::ItemIsUserCheckable);
        item->setCheckState(0, checked ? Qt::Checked : Qt::Unchecked);
        item->setData(0, Qt::UserRole, checked);
    };
    QMap<QString, QFileInfo> installed;
    if (!root.isEmpty() && plugins.exists()) {
        for (const auto &file : plugins.entryInfoList(QDir::Files | QDir::Dirs | QDir::NoDotAndDotDot)) {
            const auto name = file.fileName();
            if (!profile.native && file.isDir()) {
                const QFileInfo nested(QDir(file.filePath()).filePath(name + ".dll"));
                if (nested.isFile() && !installed.contains(name.toCaseFolded()))
                    installed.insert(name.toCaseFolded(), nested);
            } else if (file.isFile() && (profile.native ? file.suffix() == "so" :
                       file.suffix().compare("dll", Qt::CaseInsensitive) == 0)) {
                const auto stem = file.completeBaseName();
                installed.insert(profile.native ? stem : stem.toCaseFolded(), file);
            }
        }
    }
    for (const auto &file : installed) {
        const auto name = file.completeBaseName();
        const auto key = name.toCaseFolded();
        QTreeWidgetItem *item;
        if (profile.native && name == "XRSound") {
            originalSound = profile.launchWithSound();
            const bool assetsReady = !profile.xrsoundAssets.isEmpty() &&
                QFileInfo(QDir(profile.xrsoundAssets).filePath("XRSound/XRSound.cfg")).isFile();
            sound = item = row(name, assetsReady ? tr("Engine and spacecraft audio") :
                               tr("Sound assets are missing from this profile"));
            if (assetsReady || originalSound)
                check(sound, originalSound);
        } else if (profile.native && (name == "LuaInline" || name == "LuaInterpreter")) {
            item = row(name, tr("Loaded automatically for Lua scripts"));
        } else if (profile.native && name != "LuaMFD" &&
                   name != "ApolloRTCCMFD" && name != "ProjectApolloMFD") {
            item = row(name, tr("Unsupported by the native cockpit"));
        } else if (!profile.native && graphicsClient(name, file.absoluteFilePath())) {
            item = row(name, tr("Graphics client"));
            remaining.remove(key);
        } else if (name.contains(';') || name.contains('\r') || name.contains('\n') ||
                   name != name.trimmed() || QString::fromLatin1(name.toLatin1()) != name || name.size() > 250) {
            item = row(name, tr("Name cannot be stored in Orbiter.cfg"));
        } else {
            item = row(name, profile.native && name == "LuaMFD" ? tr("Lua Terminal MFD") : tr("Load at startup"));
            check(item, remaining.remove(key) != 0);
        }
        item->setToolTip(0, file.absoluteFilePath());
    }
    if (profile.native && !sound && !profile.xrsoundAssets.isEmpty()) {
        originalSound = profile.launchWithSound();
        sound = row("XRSound", tr("Plug-in missing from this installation"));
        if (originalSound)
            check(sound, true); // Allow an existing request to be cleared.
    }
    for (const auto &name : remaining) {
        auto *item = row(name, tr("Unavailable startup entry — uncheck to remove"));
        check(item, true);
    }
    if (!list->topLevelItemCount())
        layout->addWidget(new QLabel(tr("No plug-ins found in %1.").arg(plugins.absolutePath())));
    if (block.start >= 0 && block.end < 0)
        layout->addWidget(new QLabel(tr("The startup list in Orbiter.cfg is missing END_MODULES.")));
}

QMap<QString, bool> ModulesPage::startupChanges() const
{
    QMap<QString, bool> changes;
    for (int i = 0; i < list->topLevelItemCount(); ++i) {
        auto *item = list->topLevelItem(i);
        const auto initial = item->data(0, Qt::UserRole);
        const bool checked = item->checkState(0) == Qt::Checked;
        if (item != sound && initial.isValid() && checked != initial.toBool())
            changes.insert(item->text(0), checked);
    }
    return changes;
}

bool ModulesPage::soundChecked() const { return sound && sound->checkState(0) == Qt::Checked; }
bool ModulesPage::soundChanged() const { return soundChecked() != originalSound; }

QString ModulesPage::applyStartupChanges(QString &config, const QMap<QString, bool> &changes)
{
    if (changes.isEmpty())
        return {};
    auto lines = config.split('\n');
    const StartupBlock block(lines);
    if (block.start >= 0 && block.end < 0)
        return tr("Cannot edit the startup list. Restore its END_MODULES line in Orbiter.cfg.");
    const QString cr = config.contains("\r\n") ? "\r" : "";
    QStringList add;
    QSet<QString> remove;
    for (auto it = changes.cbegin(); it != changes.cend(); ++it) {
        const auto key = it.key().toCaseFolded();
        if (it.value() && !block.names.contains(key))
            add << "  " + it.key() + cr;
        if (!it.value())
            remove.insert(key);
    }
    if (block.start < 0) {
        if (!add.isEmpty()) {
            if (!config.isEmpty() && !config.endsWith('\n'))
                config += cr + '\n';
            config += "ACTIVE_MODULES" + cr + '\n' + add.join('\n') + "\nEND_MODULES" + cr + '\n';
        }
    } else {
        for (int i = 0; i < add.size(); ++i)
            lines.insert(block.end + i, add[i]);
        QStringList comments;
        for (int i = block.end - 1; i > block.start; --i) {
            if (remove.contains(lines[i].section(';', 0, 0).trimmed().toCaseFolded())) {
                const auto line = lines.takeAt(i);
                const auto comment = line.indexOf(';');
                if (comment >= 0)
                    comments.prepend(line.mid(comment));
            }
        }
        // A comment-only line inside the native list is parsed as an empty plug-in.
        for (int i = 0; i < comments.size(); ++i)
            lines.insert(block.start + i, comments[i]);
        config = lines.join('\n');
    }
    return {};
}
