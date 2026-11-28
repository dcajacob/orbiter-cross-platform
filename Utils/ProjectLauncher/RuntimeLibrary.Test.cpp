#include "RuntimeLibrary.h"
#include "../Launchpad/Launchpad.h"

#include <QApplication>
#include <QComboBox>
#include <QFile>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QPushButton>
#include <QSettings>
#include <QTemporaryDir>
#include <QTest>
#include <QTreeWidget>

static bool writeFile(const QString &path, const QByteArray &bytes)
{
    QFile file(path);
    return file.open(QIODevice::WriteOnly) && file.write(bytes) == bytes.size();
}

class LibraryTest : public QObject {
    Q_OBJECT
private slots:
    void selectRuntimeAndLaunchScenario();
#ifdef Q_OS_LINUX
    void installedUserState();
#endif
};

void LibraryTest::selectRuntimeAndLaunchScenario()
{
    QTemporaryDir temp;
    QVERIFY(temp.isValid());
    const QDir root(temp.path());
    const QString marker = root.filePath("session.json");
    const QStringList folders{"OpenGL", "Vulkan", "D3D9", "Alternate OpenGL", "Mission bundle"};
    QStringList profiles;
    for (const auto &name : folders) {
        const QDir dir(root.filePath(name));
        QVERIFY(dir.mkpath("assets/Scenarios"));
        QString engine = name == "Mission bundle" ? "run-orbiter" : "orbiter-production";
#ifdef Q_OS_WIN
        engine += ".exe";
#endif
        QVERIFY(QFile::copy(QCoreApplication::applicationFilePath(), dir.filePath(engine)));
        const QString scene = "assets/Scenarios/" + name + ".scn";
        QVERIFY(writeFile(dir.filePath(scene), "BEGIN_DESC\nTest flight\nEND_DESC\n"));
        QVERIFY(writeFile(dir.filePath("Orbiter.cfg"), {}));
        QVERIFY(writeFile(dir.filePath("Other.cfg"), {}));
        QJsonObject json{{"mode", "native"}, {"assets", "assets"}, {"modules","."}, {"planets","."},
            {"data","."}, {"executable", engine}, {"config", "Orbiter.cfg"}, {"saves", "user/saves"},
            {"scenarioConfigs", QJsonObject{{scene, "Other.cfg"}}},
            {"environment", QJsonObject{{"ORBITER_TEST_CAPTURE", marker}}}};
        if (name == "Vulkan" || name == "D3D9")
            json.insert("graphics", name.toLower());
        profiles << dir.filePath("orbiter-profile.json");
        QVERIFY(writeFile(profiles.last(), QJsonDocument(json).toJson()));
    }
    QVERIFY(root.mkpath("module-only/Modules"));
    QVERIFY(writeFile(root.filePath("module-only/module.json"), R"({"name":"SpaceX"})"));
    QVERIFY(writeFile(root.filePath("fly-runway33"), "#!/bin/sh\n"));
    QVERIFY(root.mkpath("Partial"));
    QVERIFY(writeFile(root.filePath("Partial/vulkan.json"), R"({"mode":"native","executable":"missing"})"));
    QCOMPARE(findOrbiterRuntimes({profiles.last(), root.filePath("module-only"), root.filePath("Partial")}).size(), 0);
    QCOMPARE(findOrbiterRuntimes(profiles + QStringList{root.path()}).size(), 3);
    rememberProjectRuntime(profiles.last()); // migrate a selection from the older chooser
    Launchpad window({}, profiles, true);
    window.show();
    auto *box = window.findChild<QComboBox *>("runtimeSelector");
    auto *tree = window.findChild<QTreeWidget *>("scenarioTree");
    auto *launch = window.findChild<QPushButton *>("launchButton");
    QVERIFY(box && tree && launch);
    QCOMPARE(box->count(), 3);
    QCOMPARE(box->currentData().toString(), profiles.first());
    QVERIFY(QFile::exists(":/launchpad/banner.bmp"));
    for (int i = 0; i < 3; ++i) {
        box->setCurrentIndex(i);
        QCOMPARE(box->currentText(), folders[i]);
        QVERIFY(tree->currentItem());
        QCOMPARE(tree->currentItem()->text(0), folders[i]);
        QVERIFY(launch->isEnabled());
        QTest::mouseClick(launch, Qt::LeftButton);
        QTRY_VERIFY(QFileInfo::exists(marker) && launch->isEnabled() && window.isVisible());
        QFile result(marker);
        QVERIFY(result.open(QIODevice::ReadOnly));
        const auto record = QJsonDocument::fromJson(result.readAll()).object();
        result.close();
        auto args = record.value("arguments").toVariant().toStringList();
        QDir dir(root.filePath(folders[i]));
        QCOMPARE(QFileInfo(record.value("executable").toString()).absolutePath(), dir.path());
        QCOMPARE(record.value("cwd").toString(), dir.filePath("user"));
        QCOMPARE(args.value(args.indexOf("--scenario") + 1), dir.filePath("assets/Scenarios/" + folders[i] + ".scn"));
        QCOMPARE(args.value(args.indexOf("--config") + 1), dir.filePath("Other.cfg"));
        QCOMPARE(args.value(args.indexOf("--save") + 1), dir.filePath("user/saves/Quicksave.scn"));
        if (i == 0)
            QVERIFY(!args.contains("--graphics"));
        else
            QCOMPARE(args.value(args.indexOf("--graphics") + 1), folders[i].toLower());
        QVERIFY(QFile::remove(marker));
    }
    Launchpad reopened({}, profiles, true);
    QCOMPARE(reopened.findChild<QComboBox *>("runtimeSelector")->currentText(), "D3D9");
    // A bundled mission adapter still loads its own scenarios on explicit startup.
    Launchpad bundled(profiles.last(), profiles);
    auto *bundledBox = bundled.findChild<QComboBox *>("runtimeSelector");
    QCOMPARE(bundledBox->count(), 3);
    QCOMPARE(bundledBox->currentText(), "OpenGL");
    QCOMPARE(bundled.findChild<QTreeWidget *>("scenarioTree")->currentItem()->text(0), "Mission bundle");
    QCOMPARE(lastProjectRuntime(), profiles[2]);
    QVERIFY(QFile::remove(profiles[1]));
    box->setCurrentIndex(1);
    QVERIFY(!launch->isEnabled());
    QCOMPARE(tree->topLevelItemCount(), 0);
}

#ifdef Q_OS_LINUX
void LibraryTest::installedUserState()
{
    QTemporaryDir temp;
    QVERIFY(temp.isValid());
    const QDir install(temp.path());
    qputenv("XDG_DATA_HOME", install.filePath("personal").toUtf8());
    QVERIFY(writeFile(install.filePath("stock-data-receipt.json"), "{}"));
    QVERIFY(install.mkpath("user"));
    QVERIFY(writeFile(install.filePath("user/Orbiter.cfg"), "original"));
    const QString path = install.filePath("Launchpad profile.json");
    QVERIFY(writeFile(path, R"({"mode":"native","config":"user/Orbiter.cfg","saves":"user/Scenarios"})"));
    const auto first = SimulatorProfile::load(path);
    QVERIFY(first.config.startsWith(install.filePath("personal/orbiter/installations/")));
    QVERIFY(QFileInfo(first.saveRoot).isDir());
    QVERIFY(writeFile(first.config, "personal"));
    QCOMPARE(SimulatorProfile::load(path).config, first.config);
    QFile input(first.config);
    QVERIFY(input.open(QIODevice::ReadOnly));
    QCOMPARE(input.readAll(), "personal");
}
#endif

int main(int argc, char **argv)
{
    if (qEnvironmentVariableIsSet("ORBITER_TEST_CAPTURE")) {
        QCoreApplication app(argc, argv);
        QJsonObject record{{"arguments", QJsonArray::fromStringList(app.arguments())},
            {"executable", app.applicationFilePath()}, {"cwd", QDir::currentPath()}};
        return writeFile(qEnvironmentVariable("ORBITER_TEST_CAPTURE"), QJsonDocument(record).toJson()) ? 0 : 1;
    }
    QApplication app(argc, argv);
    QTemporaryDir settings;
    if (!settings.isValid())
        return 1;
    QSettings::setDefaultFormat(QSettings::IniFormat);
    QSettings::setPath(QSettings::IniFormat, QSettings::UserScope, settings.path());
    app.setOrganizationName("OrbiterLauncherTest");
    app.setApplicationName("Orbiter Launchpad");
    LibraryTest test;
    return QTest::qExec(&test, argc, argv);
}

#include "RuntimeLibrary.Test.moc"
