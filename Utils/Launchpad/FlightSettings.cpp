#include "FlightSettings.h"
#include "ModulesPage.h"
#include "SimulatorProfile.h"

#include <QCheckBox>
#include <QDialog>
#include <QDialogButtonBox>
#include <QDoubleSpinBox>
#include <QFile>
#include <QFileInfo>
#include <QFormLayout>
#include <QLockFile>
#include <QMap>
#include <QMessageBox>
#include <QRegularExpression>
#include <QSaveFile>
#include <QTabWidget>
#include <QVBoxLayout>

namespace {
// Match the first active assignment, as Orbiter does. Capture only its value
// so comments, CRLF, and unedited keys survive the rewrite.
QRegularExpressionMatch assignment(const QString &text, const QString &key)
{
    return QRegularExpression("^" + key + "[ \\t]*=[ \\t]*([^;\\r\\n]*?)[ \\t]*(?=;|\\r?$)",
                              QRegularExpression::MultilineOption).match(text);
}

using Values = QMap<QString, QString>;

QString saveChanges(const QString &path, const QString &original, const Values &before, const Values &after,
                    const ModulesPage &modules, const SimulatorProfile &profile)
{
    const auto moduleChanges = modules.startupChanges();
    const bool configChanged = before != after || !moduleChanges.isEmpty();
    if (!configChanged && !modules.soundChanged())
        return {};
    QLockFile lock(path + ".launchpad.lock");
    if (!lock.tryLock(0))
        return QObject::tr("Could not lock the configuration for writing: %1").arg(path);
    if (!configChanged)
        return profile.setLaunchWithSound(modules.soundChecked());
    QFile input(path);
    if (!QFileInfo(input).isWritable() || !input.open(QIODevice::ReadOnly))
        return QObject::tr("Cannot edit the configuration: %1").arg(path);
    auto text = QString::fromLatin1(input.readAll());
    if (input.error() != QFileDevice::NoError)
        return input.errorString();
    input.close();
    const auto newline = text.contains("\r\n") ? "\r\n" : "\n";
    for (auto it = after.cbegin(); it != after.cend(); ++it) {
        if (it.value() == before.value(it.key()))
            continue;
        const auto old = assignment(original, it.key());
        const auto current = assignment(text, it.key());
        if (old.hasMatch() != current.hasMatch() || old.captured(1) != current.captured(1))
            return QObject::tr("%1 changed outside Launchpad. Reopen Flight settings to load the new value.").arg(it.key());
        if (current.hasMatch())
            text.replace(current.capturedStart(1), current.capturedLength(1), it.value());
        else
            text.prepend(it.key() + " = " + it.value() + newline);
    }
    const auto moduleError = ModulesPage::applyStartupChanges(text, moduleChanges);
    if (!moduleError.isEmpty())
        return moduleError;
    QSaveFile output(path);
    const auto bytes = text.toLatin1();
    if (!output.open(QIODevice::WriteOnly) || output.write(bytes) != bytes.size())
        return output.errorString();
    // Stage the config before saving the separate Launchpad audio preference.
    const bool previousSound = profile.launchWithSound();
    if (modules.soundChanged()) {
        const auto error = profile.setLaunchWithSound(modules.soundChecked());
        if (!error.isEmpty())
            return error;
    }
    if (!output.commit()) {
        if (modules.soundChanged()) {
            const auto error = profile.setLaunchWithSound(previousSound);
            if (!error.isEmpty())
                return output.errorString() + "\n" + error;
        }
        return output.errorString();
    }
    return {};
}
}

void showFlightSettings(QWidget *parent, const SimulatorProfile &profile)
{
    const auto path = QFileInfo(profile.config).canonicalFilePath();
    QFile file(path);
    if (!file.open(QIODevice::ReadOnly)) {
        QMessageBox::warning(parent, QObject::tr("Flight settings"),
                             QObject::tr("Could not read %1.").arg(profile.config));
        return;
    }
    const auto original = QString::fromLatin1(file.readAll());
    if (file.error() != QFileDevice::NoError) {
        QMessageBox::warning(parent, QObject::tr("Flight settings"), file.errorString());
        return;
    }
    file.close();
    QDialog dialog(parent);
    dialog.setObjectName("flightSettings");
    dialog.setWindowTitle(QObject::tr("Flight settings"));
    auto *layout = new QVBoxLayout(&dialog);
    layout->setContentsMargins(16, 16, 16, 16);
    layout->setSpacing(12);
    auto *tabs = new QTabWidget;
    layout->addWidget(tabs);
    auto *options = new QWidget;
    auto *form = new QFormLayout(options);
    tabs->addTab(options, QObject::tr("Options"));

    auto addNumber = [&](QFormLayout *page, const QString &key, const QString &label,
                         double fallback, double low, double high, int decimals, const QString &suffix = {}) {
        auto *field = new QDoubleSpinBox;
        field->setObjectName(key);
        field->setDecimals(decimals);
        field->setRange(low, high);
        field->setSingleStep(decimals ? 0.01 : 1);
        field->setSuffix(suffix);
        bool ok;
        const double value = assignment(original, key).captured(1).toDouble(&ok);
        field->setValue(ok ? value : fallback);
        page->addRow(label, field);
    };
    auto *limitedFuel = new QCheckBox(QObject::tr("Limited fuel"));
    limitedFuel->setObjectName("limitedFuel");
    limitedFuel->setChecked(!assignment(original, "UnlimitedFuel").captured(1).startsWith("TRUE", Qt::CaseInsensitive));
    form->addRow(limitedFuel);
    addNumber(form, "GenericMFDSize", QObject::tr("Glass cockpit MFD size"), 6, 1, 10, 0);
    addNumber(form, "InstrumentUpdateInterval", QObject::tr("MFD update interval"), 0.5, 0.01, 1e9, 2, QObject::tr(" s"));
    addNumber(form, "PanelScale", QObject::tr("2D panel scale"), 1, 0.25, 4, 2, QObject::tr(" ×"));
    if (profile.native) {
        auto *video = new QWidget;
        auto *videoForm = new QFormLayout(video);
        tabs->addTab(video, QObject::tr("Video"));
        addNumber(videoForm, "WindowWidth", QObject::tr("Window width"), 1280, 320, 16384, 0, QObject::tr(" px"));
        addNumber(videoForm, "WindowHeight", QObject::tr("Window height"), 720, 200, 16384, 0, QObject::tr(" px"));
    }

    auto *modules = new ModulesPage(profile, original);
    tabs->addTab(modules, QObject::tr("Modules"));

    auto values = [&] {
        Values result;
        result.insert("UnlimitedFuel", limitedFuel->isChecked() ? "FALSE" : "TRUE");
        for (auto *field : tabs->findChildren<QDoubleSpinBox *>())
            result.insert(field->objectName(), QString::number(field->value(), 'f', field->decimals()));
        return result;
    };
    const auto before = values();
    auto *buttons = new QDialogButtonBox(QDialogButtonBox::Save | QDialogButtonBox::Cancel);
    layout->addWidget(buttons);
    QObject::connect(buttons, &QDialogButtonBox::rejected, &dialog, &QDialog::reject);
    QObject::connect(buttons, &QDialogButtonBox::accepted, &dialog, [&] {
        const auto error = saveChanges(path, original, before, values(), *modules, profile);
        if (error.isEmpty())
            dialog.accept();
        else
            QMessageBox::warning(&dialog, dialog.windowTitle(), error);
    });
    dialog.exec();
}
