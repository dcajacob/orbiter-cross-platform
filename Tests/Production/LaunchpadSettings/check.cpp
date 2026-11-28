#include "FlightSettings.h"
#include "ModulesPage.h"
#include "SimulatorProfile.h"

#include <QApplication>
#include <QCheckBox>
#include <QComboBox>
#include <QDialog>
#include <QDialogButtonBox>
#include <QDoubleSpinBox>
#include <QFile>
#include <QMessageBox>
#include <QPushButton>
#include <QScopeGuard>
#include <QSettings>
#include <QSpinBox>
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
    void savedFlightConfigurations()
    {
        QTemporaryDir dir;
        QVERIFY(dir.isValid());
        QCoreApplication::setOrganizationName("orbiter-launchpad-test");
        QSettings::setDefaultFormat(QSettings::IniFormat);
        QSettings::setPath(QSettings::IniFormat, QSettings::UserScope, dir.path());
        const auto profilePath = dir.filePath("profile.json");
        writeFile(profilePath, R"({"mode":"native","config":"Orbiter.cfg","xrsoundAssets":"sound",
            "scenarioConfigs":{"Scenarios/Cloudy.scn":"settings/Cloudy.cfg"}})");
        writeFile(dir.filePath("Orbiter.cfg"));
        const auto base = SimulatorProfile::load(profilePath);
        const auto scene = dir.filePath("Scenarios/Cloudy.scn");
        const auto cloudy = base.forScenario(scene);
        const auto arguments = cloudy.arguments(scene, false);
        QCOMPARE(arguments.value(arguments.indexOf("--config") + 1), dir.filePath("settings/Cloudy.cfg"));
        QCOMPARE(cloudy.forScenario(dir.filePath("stock/Cloudy.scn")).config, base.config);
        QVERIFY(base.setLaunchWithSound(false).isEmpty());
        QVERIFY(!cloudy.arguments(scene, false).contains("--xrsound-assets"));
        QVERIFY(cloudy.setLaunchWithSound(true).isEmpty());
        QVERIFY(base.launchWithSound());
    }

    void planetVisualEffects()
    {
        QTemporaryDir dir;
        SimulatorProfile profile;
        profile.native = true;
        profile.config = dir.filePath("Orbiter.cfg");
        const QByteArray original = "; preserved\r\nEnableNightlights = true ; cities\r\n";
        writeFile(profile.config, original);
        for (int pass = 0; pass < 3; ++pass) {
            QTimer::singleShot(0, [&] {
                auto *dialog = qobject_cast<QDialog *>(QApplication::activeModalWidget());
                const auto closeOnFailure = qScopeGuard([&] { if (dialog->isVisible()) dialog->reject(); });
                auto *clouds = dialog->findChild<QCheckBox *>("EnableClouds");
                auto *shadows = dialog->findChild<QCheckBox *>("EnableCloudShadows");
                auto *lights = dialog->findChild<QCheckBox *>("EnableNightlights");
                auto *detail = dialog->findChild<QDoubleSpinBox *>("PlanetMaxPatchLevel");
                QVERIFY(clouds && shadows && lights && detail);
                QCOMPARE(clouds->isChecked(), pass < 2);
                QCOMPARE(shadows->isEnabled(), clouds->isChecked());
                QCOMPARE(shadows->isChecked(), pass == 2);
                QCOMPARE(lights->isChecked(), pass < 2);
                QCOMPARE(detail->minimum(), 1.0);
                QCOMPARE(detail->maximum(), 21.0);
                QCOMPARE(detail->value(), pass < 2 ? 21.0 : 1.0);
                if (pass < 2) {
                    shadows->click();
                    clouds->click();
                    QVERIFY(!shadows->isEnabled() && shadows->isChecked());
                    lights->click();
                    detail->setValue(1);
                } else {
                    clouds->click();
                    QVERIFY(shadows->isEnabled() && shadows->isChecked());
                }
                dialog->findChild<QDialogButtonBox *>()->button(pass == 1 ? QDialogButtonBox::Save : QDialogButtonBox::Cancel)->click();
            });
            showFlightSettings(nullptr, profile);
            QFile cfg(profile.config);
            QVERIFY(cfg.open(QIODevice::ReadOnly));
            const auto bytes = cfg.readAll();
            if (!pass) QCOMPARE(bytes, original);
            else {
                QVERIFY(bytes.contains("EnableClouds = FALSE\r\n"));
                QVERIFY(bytes.contains("EnableCloudShadows = TRUE\r\n"));
                QVERIFY(bytes.contains("PlanetMaxPatchLevel = 1\r\n"));
                QVERIFY(bytes.endsWith("; preserved\r\nEnableNightlights = FALSE ; cities\r\n"));
            }
        }
    }
#ifdef Q_OS_LINUX
    void extraSettings()
    {
        QTemporaryDir dir;
        SimulatorProfile profile;
        profile.native = true;
        profile.config = dir.filePath("Orbiter.cfg");
        profile.assets = dir.filePath("Stock");
        profile.modules = dir.filePath("Modules");
        QDir().mkpath(profile.assets + "/Textures2/DG");
        QDir().mkpath(profile.modules + "/Celbody/Earth/Atmosphere");
        writeFile(profile.modules + "/Celbody/Earth/Atmosphere/EarthAtm2006.so");
        const QByteArray original = "PropStage0 = 0 0.1 0.0034906585039886587 0.5 0.0174532925199433 ; keep\r\n"
                                    "StabilisePLimit = 0.05\r\nForceMfdPow2 = AUTO\r\nFixedStep = 1\r\n";
        writeFile(profile.config, original);
        for (int pass = 0; pass < 3; ++pass) {
            QTimer::singleShot(0, [&] {
                auto *dialog = qobject_cast<QDialog *>(QApplication::activeModalWidget());
                const auto closeOnFailure = qScopeGuard([&] { if (dialog->isVisible()) dialog->reject(); });
                auto *count = dialog->findChild<QSpinBox *>("PropStages");
                auto *method = dialog->findChild<QComboBox *>("PropStage0Method");
                auto *percent = dialog->findChild<QDoubleSpinBox *>("StabilisePLimit");
                auto *resolution = dialog->findChild<QComboBox *>("ForceMfdPow2");
                auto *atmosphere = dialog->findChild<QComboBox *>("NativeAtmosphere_Earth");
                auto *texture = dialog->findChild<QComboBox *>("NativeDGHighResTextures");
                QVERIFY(count && method && percent && resolution && atmosphere && texture);
                QCOMPARE(count->value(), pass == 2 ? 1 : 4);
                QCOMPARE(method->currentText(), pass == 2 ? "RK7" : "RK2");
                QCOMPARE(percent->value(), pass == 2 ? 2.5 : 5.0);
                QCOMPARE(atmosphere->currentData().toString(), pass == 2 ? "EarthAtm2006" : "DEFAULT");
                QCOMPARE(texture->currentData().toString(), pass == 2 ? "FALSE" : "DEFAULT");
                auto *threshold = dialog->findChild<QSpinBox *>("MfdHiresThreshold");
                QCOMPARE(threshold->isEnabled(), pass == 2);
                count->setValue(1);
                method->setCurrentText("RK7");
                percent->setValue(2.5);
                resolution->setCurrentIndex(resolution->findData("TRUE"));
                atmosphere->setCurrentIndex(atmosphere->findData("EarthAtm2006"));
                texture->setCurrentIndex(texture->findData("FALSE"));
                auto *buttons = dialog->findChild<QDialogButtonBox *>();
                buttons->button(pass ? QDialogButtonBox::Save : QDialogButtonBox::Cancel)->click();
            });
            showFlightSettings(nullptr, profile);
            QFile cfg(profile.config);
            QVERIFY(cfg.open(QIODevice::ReadOnly));
            const auto bytes = cfg.readAll();
            if (pass == 0) QCOMPARE(bytes, original);
            else {
                QVERIFY(bytes.contains("PropStage0 = 4 0.1 0.0034906585039886587 0.5 0.0174532925199433 ; keep\r\n"));
                QVERIFY(bytes.contains("StabilisePLimit = 0.025\r\n"));
                QVERIFY(bytes.contains("FixedStep = 1\r\n"));
                QVERIFY(!bytes.contains("PropStage1"));
            }
        }
    }

    void extraStageLimits()
    {
        QTemporaryDir dir;
        SimulatorProfile profile;
        profile.native = true;
        profile.config = dir.filePath("Orbiter.cfg");
        writeFile(profile.config, "PropStages = 3\n");
        for (bool concurrent : {false, true}) {
            QString warning;
            QTimer::singleShot(0, [&] {
                auto *d = qobject_cast<QDialog *>(QApplication::activeModalWidget());
                const auto closeOnFailure = qScopeGuard([&] { if (d->isVisible()) d->reject(); });
                auto *method = d->findChild<QComboBox *>("PropStage0Method");
                QVERIFY(method);
                QCOMPARE(method->currentText(), "RK4");
                auto *limit = d->findChild<QDoubleSpinBox *>("PropStage0Field2");
                limit->setValue(concurrent ? 0.6 : 10);
                if (concurrent) writeFile(profile.config, "PropStages = 2\n");
                QTimer::singleShot(0, [&] {
                    if (auto *msg = qobject_cast<QMessageBox *>(QApplication::activeModalWidget())) {
                        warning = msg->text();
                        msg->accept();
                    }
                });
                d->findChild<QDialogButtonBox *>()->button(QDialogButtonBox::Save)->click();
                d->reject();
            });
            showFlightSettings(nullptr, profile);
            QVERIFY2(warning.contains(concurrent ? "PropStages" : "stage 2"), qPrintable(warning));
            QFile file(profile.config);
            QVERIFY(file.open(QIODevice::ReadOnly));
            QCOMPARE(file.readAll(), concurrent ? "PropStages = 2\n" : "PropStages = 3\n");
        }
    }

    void linuxDisplayModes()
    {
        QTemporaryDir dir;
        SimulatorProfile profile;
        profile.native = true;
        profile.config = dir.filePath("Orbiter.cfg");
        const QByteArray original = "WindowWidth = 960\r\nWindowHeight = 600\r\n";
        writeFile(profile.config, original);
        for (int pass = 0; pass < 3; ++pass) {
            QTimer::singleShot(0, [&] {
                auto *dialog = qobject_cast<QDialog *>(QApplication::activeModalWidget());
                const auto closeOnFailure = qScopeGuard([&] { if (dialog->isVisible()) dialog->reject(); });
                auto *full = dialog->findChild<QCheckBox *>("fullscreen");
                auto *sync = dialog->findChild<QCheckBox *>("vsync");
                auto *width = dialog->findChild<QDoubleSpinBox *>("WindowWidth");
                QVERIFY(full && sync && width);
                QCOMPARE(full->isChecked(), pass == 2);
                QCOMPARE(sync->isChecked(), pass != 2);
                full->click();
                sync->click();
                QCOMPARE(width->isHidden(), full->isChecked());
                QCOMPARE(width->value(), 960);
                auto *buttons = dialog->findChild<QDialogButtonBox *>();
                buttons->button(pass == 0 ? QDialogButtonBox::Cancel : QDialogButtonBox::Save)->click();
            });
            showFlightSettings(nullptr, profile);
            QFile cfg(profile.config);
            QVERIFY(cfg.open(QIODevice::ReadOnly));
            const auto bytes = cfg.readAll();
            QVERIFY(bytes.endsWith(original));
            if (pass == 0)
                QCOMPARE(bytes, original);
            else {
                QVERIFY(bytes.contains(pass == 1 ? "Fullscreen = TRUE\r\n" : "Fullscreen = FALSE\r\n"));
                QVERIFY(bytes.contains(pass == 1 ? "NoVSync = TRUE\r\n" : "NoVSync = FALSE\r\n"));
            }
        }
    }
#endif
    void linkedSizeConflict()
    {
        QTemporaryDir dir;
        SimulatorProfile profile;
        profile.native = true;
        profile.config = dir.filePath("Orbiter.cfg");
        writeFile(profile.config, "WindowWidth = 1000\nWindowHeight = 731\n");
        const QByteArray external = "WindowWidth = 1024\nWindowHeight = 731\n";
        bool warned = false;
        QTimer::singleShot(0, [&] {
            auto *dialog = qobject_cast<QDialog *>(QApplication::activeModalWidget());
            dialog->findChild<QComboBox *>("windowAspectRatio")->setCurrentText("16:10");
            writeFile(profile.config, external);
            QTimer::singleShot(0, dialog, [&] {
                if (auto *message = qobject_cast<QMessageBox *>(QApplication::activeModalWidget())) {
                    warned = message->text().contains("WindowWidth");
                    message->accept();
                }
            });
            dialog->findChild<QDialogButtonBox *>()->button(QDialogButtonBox::Save)->click();
            dialog->reject();
        });
        showFlightSettings(nullptr, profile);
        QVERIFY(warned);
        QFile cfg(profile.config);
        QVERIFY(cfg.open(QIODevice::ReadOnly));
        QCOMPARE(cfg.readAll(), external);
    }

    void videoWindowSizing()
    {
        QTemporaryDir dir;
        SimulatorProfile profile;
        profile.native = true;
        profile.config = dir.filePath("Orbiter.cfg");
        const QByteArray original = "WindowWidth = 1000 ; pixels\r\nWindowHeight = 731\r\n"
                                    "DeviceNoVSync = TRUE\r\n";
        writeFile(profile.config, original);
        for (auto action : {QDialogButtonBox::Cancel, QDialogButtonBox::Save}) {
            QTimer::singleShot(0, [&] {
                auto *dialog = qobject_cast<QDialog *>(QApplication::activeModalWidget());
                const auto closeOnFailure = qScopeGuard([&] { if (dialog->isVisible()) dialog->reject(); });
                auto *ratio = dialog->findChild<QComboBox *>("windowAspectRatio");
                auto *width = dialog->findChild<QDoubleSpinBox *>("WindowWidth");
                auto *height = dialog->findChild<QDoubleSpinBox *>("WindowHeight");
                QVERIFY(ratio && width && height);
                QCOMPARE(ratio->currentText(), "Free");
                width->setValue(960);
                QCOMPARE(height->value(), 731);
                ratio->setCurrentText("4:3");
                QCOMPARE(height->value(), 720);
                ratio->setCurrentText("16:10");
                QCOMPARE(height->value(), 600);
                ratio->setCurrentText("16:9");
                QCOMPARE(height->value(), 540);
                width->setValue(320);
                QCOMPARE(width->value(), 356);
                QCOMPARE(height->value(), 200);
                height->setValue(16384);
                QCOMPARE(width->value(), 16384);
                QCOMPARE(height->value(), 9216);
                height->setValue(600);
                QCOMPARE(width->value(), 1066);
                dialog->findChild<QDialogButtonBox *>()->button(action)->click();
            });
            showFlightSettings(nullptr, profile);
            QFile cfg(profile.config);
            QVERIFY(cfg.open(QIODevice::ReadOnly));
            QByteArray expected = original;
            if (action == QDialogButtonBox::Save)
                expected.replace("1000", "1066").replace("731", "600");
            QCOMPARE(cfg.readAll(), expected);
        }
        QTimer::singleShot(0, [&] {
            auto *dialog = qobject_cast<QDialog *>(QApplication::activeModalWidget());
            const auto close = qScopeGuard([&] { dialog->reject(); });
            QCOMPARE(dialog->findChild<QComboBox *>("windowAspectRatio")->currentText(), "16:9");
            QCOMPARE(dialog->findChild<QDoubleSpinBox *>("WindowHeight")->value(), 600);
        });
        showFlightSettings(nullptr, profile);
    }

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
        for (const auto *name : {"LuaMFD.so", "XRSound.so", "LuaInline.so", "LuaInterpreter.so",
                                 "ApolloRTCCMFD.so", "ProjectApolloMFD.so", "Other.so"})
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
                for (const auto *name : {"ApolloRTCCMFD", "ProjectApolloMFD"}) {
                    auto *item = plugin(page, name);
                    if (!item || !item->flags().testFlag(Qt::ItemIsUserCheckable))
                        qFatal("Expected a selectable Apollo MFD");
                    item->setCheckState(0, Qt::Checked);
                }
                sound->setCheckState(0, Qt::Unchecked);
                dialog->findChild<QDialogButtonBox *>()->button(action)->click();
            });
            showFlightSettings(nullptr, profile);
            QFile config(profile.config);
            QVERIFY(config.open(QIODevice::ReadOnly));
            const bool saved = action == QDialogButtonBox::Save;
            QCOMPARE(config.readAll(), saved ? original + "ACTIVE_MODULES\r\n  ApolloRTCCMFD\r\n  LuaMFD\r\n  ProjectApolloMFD\r\nEND_MODULES\r\n" : original);
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
