#include "FlightSettings.h"
#include "SimulatorProfile.h"

#include <QApplication>
#include <QCheckBox>
#include <QDialogButtonBox>
#include <QDoubleSpinBox>
#include <QFile>
#include <QPushButton>
#include <QTemporaryDir>
#include <QTest>
#include <QTimer>

class FlightSettingsCheck : public QObject {
    Q_OBJECT
private slots:
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
