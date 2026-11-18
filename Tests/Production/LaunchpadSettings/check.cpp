#include "FlightSettings.h"
#include "ModulesPage.h"
#include "SimulatorProfile.h"

#include <QApplication>
#include <QCheckBox>
#include <QDialogButtonBox>
#include <QDoubleSpinBox>
#include <QFile>
#include <QPushButton>
#include <QSettings>
#include <QTabWidget>
#include <QTemporaryDir>
#include <QTest>
#include <QTimer>
#include <QTreeWidget>

namespace {
void writeFile(const QString &path, const QByteArray &bytes = {})
{
    QFile file(path);
    if (!file.open(QIODevice::WriteOnly) || file.write(bytes) != bytes.size())
        qFatal("Cannot create test file");
}

QTreeWidgetItem *plugin(QWidget *page, const QString &name)
{
    const auto matches = page->findChild<QTreeWidget *>("moduleList")->findItems(name, Qt::MatchExactly);
    return matches.size() == 1 ? matches.first() : nullptr;
}
}

class FlightSettingsCheck : public QObject {
    Q_OBJECT
private slots:
    void nativeModules()
    {
        QTemporaryDir dir;
        QVERIFY(dir.isValid());
        QCoreApplication::setOrganizationName("orbiter-launchpad-test");
        QSettings::setDefaultFormat(QSettings::IniFormat);
        QSettings::setPath(QSettings::IniFormat, QSettings::UserScope, dir.path());
        SimulatorProfile profile;
        profile.native = true;
        profile.modules = dir.path();
        profile.config = dir.filePath("Orbiter.cfg");
        profile.xrsoundAssets = dir.path();
        QVERIFY(QDir(dir.path()).mkdir("Plugin"));
        QVERIFY(QDir(dir.path()).mkdir("XRSound"));
        writeFile(dir.filePath("XRSound/XRSound.cfg"));
        for (const auto *name : {"LuaMFD.so", "XRSound.so", "LuaInline.so", "LuaInterpreter.so", "Other.so"})
            writeFile(dir.filePath("Plugin/" + QString(name)));
        const QByteArray original = "; native config\r\n";
        writeFile(profile.config, original);
        QVERIFY(profile.arguments("flight.scn", true).contains("--xrsound-assets"));
        for (auto action : {QDialogButtonBox::Cancel, QDialogButtonBox::Save}) {
            QTimer::singleShot(0, [&] {
                auto *dialog = QApplication::activeModalWidget();
                auto *page = dialog->findChild<QWidget *>("modulesPage");
                dialog->findChild<QTabWidget *>()->setCurrentWidget(page);
                auto *lua = plugin(page, "LuaMFD"), *sound = plugin(page, "XRSound");
                if (!lua || !sound || lua->checkState(0) != Qt::Unchecked || sound->checkState(0) != Qt::Checked)
                    qFatal("Incorrect initial module selection");
                for (const auto *name : {"LuaInline", "LuaInterpreter", "Other"}) {
                    auto *item = plugin(page, name);
                    if (!item || item->flags().testFlag(Qt::ItemIsUserCheckable))
                        qFatal("Expected a read-only module");
                }
                lua->setCheckState(0, Qt::Checked);
                sound->setCheckState(0, Qt::Unchecked);
                dialog->findChild<QDialogButtonBox *>()->button(action)->click();
            });
            showFlightSettings(nullptr, profile);
            QFile config(profile.config);
            QVERIFY(config.open(QIODevice::ReadOnly));
            const bool saved = action == QDialogButtonBox::Save;
            QCOMPARE(config.readAll(), saved ? original + "ACTIVE_MODULES\r\n  LuaMFD\r\nEND_MODULES\r\n" : original);
            QCOMPARE(profile.arguments("flight.scn", true).contains("--xrsound-assets"), !saved);
        }
        profile.config = dir.filePath("other.cfg");
        writeFile(profile.config);
        QVERIFY(profile.launchWithSound());
    }

    void classicDiscoveryAndMerge()
    {
        QTemporaryDir dir;
        QVERIFY(QDir(dir.path()).mkpath("Modules/Plugin/Nested"));
        for (const auto *path : {"Direct.dll", "OGLClient.dll", "Nested/Nested.dll", "ignore.so"})
            writeFile(dir.filePath("Modules/Plugin/" + QString(path)));
        auto profile = SimulatorProfile::fromWindowsExecutable(dir.filePath("orbiter.exe"));
        QString cfg = "; header\r\nactive_modules\r\n  OGLClient\r\n  DIRECT ; old\r\n"
                      "  Direct\r\n  Missing\r\nEND_MODULES\r\nPanelScale = 1\r\n";
        ModulesPage page(profile, cfg);
        QVERIFY(plugin(&page, "Direct") && plugin(&page, "Nested") && plugin(&page, "Missing"));
        QVERIFY(!plugin(&page, "ignore"));
        QVERIFY(!plugin(&page, "OGLClient")->flags().testFlag(Qt::ItemIsUserCheckable));
        QCOMPARE(plugin(&page, "Direct")->checkState(0), Qt::Checked);
        QCOMPARE(plugin(&page, "Missing")->checkState(0), Qt::Checked);
        plugin(&page, "Direct")->setCheckState(0, Qt::Unchecked);
        plugin(&page, "Nested")->setCheckState(0, Qt::Checked);
        cfg.replace("  Missing", "  AddedElsewhere\r\n  Missing");
        QVERIFY(ModulesPage::applyStartupChanges(cfg, page.startupChanges()).isEmpty());
        QCOMPARE(cfg, "; header\r\n; old\r\nactive_modules\r\n  OGLClient\r\n  AddedElsewhere\r\n"
                      "  Missing\r\n  Nested\r\nEND_MODULES\r\nPanelScale = 1\r\n");
        QString broken = "ACTIVE_MODULES\n  Direct";
        QVERIFY(!ModulesPage::applyStartupChanges(broken, page.startupChanges()).isEmpty());
        QCOMPARE(broken, "ACTIVE_MODULES\n  Direct");
    }

    void preserveConfigOnCancelAndSave()
    {
        QTemporaryDir dir;
        QVERIFY(dir.isValid());
        SimulatorProfile profile;
        profile.native = true;
        profile.config = dir.filePath("Orbiter.cfg");
        const QByteArray original = "; label \xe9\r\nPanelScale = 1.0  ; cockpit\r\n"
                                    "ACTIVE_MODULES\r\n  XRSound\r\nEND_MODULES\r\n";
        QFile config(profile.config);
        QVERIFY(config.open(QIODevice::WriteOnly));
        QCOMPARE(config.write(original), original.size());
        config.close();

        for (auto action : {QDialogButtonBox::Cancel, QDialogButtonBox::Save}) {
            QTimer::singleShot(0, [&] {
                auto *dialog = QApplication::activeModalWidget();
                auto *panel = dialog->findChild<QDoubleSpinBox *>("PanelScale");
                auto *fuel = dialog->findChild<QCheckBox *>("limitedFuel");
                auto *buttons = dialog->findChild<QDialogButtonBox *>();
                panel->setValue(1.25);
                fuel->setChecked(false);
                if (action == QDialogButtonBox::Save) {
                    QFile external(profile.config);
                    if (!external.open(QIODevice::Append) || external.write("; concurrent edit\r\n") < 0)
                        qFatal("Could not stage concurrent config edit");
                }
                buttons->button(action)->click();
            });
            showFlightSettings(nullptr, profile);
            QVERIFY(config.open(QIODevice::ReadOnly));
            QByteArray expected = original;
            if (action == QDialogButtonBox::Save) {
                expected.prepend("UnlimitedFuel = TRUE\r\n");
                expected.replace("1.0  ;", "1.25  ;");
                expected.append("; concurrent edit\r\n");
            }
            QCOMPARE(config.readAll(), expected);
            config.close();
        }
    }
};

QTEST_MAIN(FlightSettingsCheck)
#include "check.moc"
