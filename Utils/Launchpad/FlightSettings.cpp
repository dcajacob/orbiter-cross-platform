#include "FlightSettings.h"
#include "ExtraPage.h"
#include "ModulesPage.h"
#include "SimulatorProfile.h"

#include <algorithm>
#include <QCheckBox>
#include <QComboBox>
#include <QDialog>
#include <QDialogButtonBox>
#include <QDoubleSpinBox>
#include <QFile>
#include <QFileInfo>
#include <QFormLayout>
#include <QGroupBox>
#include <QLabel>
#include <QLockFile>
#include <QMap>
#include <QMessageBox>
#include <QRegularExpression>
#include <QSaveFile>
#include <QSignalBlocker>
#include <QTabWidget>
#include <QVBoxLayout>

namespace {
// Match the first active assignment, as Orbiter does. Capture only its value
// so comments, CRLF, and unedited keys survive the rewrite.
QRegularExpressionMatch assignment(const QString &text, const QString &key)
{
    return QRegularExpression("^" + QRegularExpression::escape(key) + "[ \\t]*=[ \\t]*([^;\\r\\n]*?)[ \\t]*(?=;|\\r?$)",
                              QRegularExpression::MultilineOption).match(text);
}

using Values = QMap<QString, QString>;

bool stagesChanged(const Values &before, const Values &after)
{
    return std::any_of(after.keyValueBegin(), after.keyValueEnd(), [&](const auto &entry) {
        return entry.first.startsWith("PropStage") && entry.second != before.value(entry.first);
    });
}

QComboBox *addAspectRatio(QFormLayout *form, QDoubleSpinBox *width, QDoubleSpinBox *height)
{
    auto *ratio = new QComboBox;
    ratio->setObjectName("windowAspectRatio");
    ratio->addItem(QObject::tr("Free"));
    for (const QSize size : {QSize(4, 3), QSize(16, 10), QSize(16, 9)}) {
        ratio->addItem(QString("%1:%2").arg(size.width()).arg(size.height()), size);
        // The Windows launcher infers the lock from either integer-rounded dimension.
        const int w = int(width->value()), h = int(height->value());
        if (w == h * size.width() / size.height() || h == w * size.height() / size.width())
            ratio->setCurrentIndex(ratio->count() - 1);
    }
    form->addRow(QObject::tr("&Aspect ratio"), ratio);
    width->setKeyboardTracking(false);
    height->setKeyboardTracking(false);
    auto update = [ratio, width, height](bool fromWidth) {
        if (!ratio->currentData().isValid())
            return;
        const QSize size = ratio->currentData().toSize();
        auto *edited = fromWidth ? width : height;
        auto *other = fromWidth ? height : width;
        const int from = fromWidth ? size.width() : size.height();
        const int to = fromWidth ? size.height() : size.width();
        // Bound the edited side too, so its partner fits the renderer's pixel limits.
        const int low = (int(other->minimum()) * from + to - 1) / to;
        const int high = ((int(other->maximum()) + 1) * from - 1) / to;
        const int value = qBound(low, int(edited->value()), high);
        const QSignalBlocker blockEdited(edited), blockOther(other);
        edited->setValue(value);
        other->setValue(value * to / from);
    };
    QObject::connect(ratio, &QComboBox::currentIndexChanged, ratio, [update] { update(true); });
    QObject::connect(width, &QDoubleSpinBox::valueChanged, ratio, [update] { update(true); });
    QObject::connect(height, &QDoubleSpinBox::valueChanged, ratio, [update] { update(false); });
    return ratio;
}

QString saveChanges(const QString &path, const QString &original, const Values &before, const Values &after,
                    const ModulesPage &modules, const SimulatorProfile &profile, bool linkedSize)
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
    const bool checkBothDimensions = linkedSize && (before.value("WindowWidth") != after.value("WindowWidth")
        || before.value("WindowHeight") != after.value("WindowHeight"));
    const bool checkStages = stagesChanged(before, after);
    for (auto it = after.cbegin(); it != after.cend(); ++it) {
        const bool changed = it.value() != before.value(it.key());
        if (!changed && !(checkStages && it.key().startsWith("PropStage")) && !(checkBothDimensions && (it.key() == "WindowWidth" || it.key() == "WindowHeight")))
            continue;
        const auto old = assignment(original, it.key());
        const auto current = assignment(text, it.key());
        if (old.hasMatch() != current.hasMatch() || old.captured(1) != current.captured(1))
            return QObject::tr("%1 changed outside Launchpad. Reopen Flight settings to load the new value.").arg(it.key());
        if (!changed)
            continue;
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

    QList<QDoubleSpinBox *> numericFields;
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
        numericFields.append(field);
        page->addRow(label, field);
        return field;
    };
    auto *limitedFuel = new QCheckBox(QObject::tr("Limited fuel"));
    limitedFuel->setObjectName("limitedFuel");
    limitedFuel->setChecked(!assignment(original, "UnlimitedFuel").captured(1).startsWith("TRUE", Qt::CaseInsensitive));
    form->addRow(limitedFuel);
    addNumber(form, "GenericMFDSize", QObject::tr("Glass cockpit MFD size"), 6, 1, 10, 0);
    addNumber(form, "InstrumentUpdateInterval", QObject::tr("MFD update interval"), 0.5, 0.01, 1e9, 2, QObject::tr(" s"));
    addNumber(form, "PanelScale", QObject::tr("2D panel scale"), 1, 0.25, 4, 2, QObject::tr(" ×"));
    auto *visual = new QGroupBox(QObject::tr("Visual effects"));
    auto *visualForm = new QFormLayout(visual);
    form->addRow(visual);
    QList<QCheckBox *> visualFlags;
    auto addVisualFlag = [&](const QString &key, const QString &label, bool enabledByDefault) {
        auto *field = new QCheckBox(label);
        field->setObjectName(key);
        const auto value = assignment(original, key).captured(1);
        field->setChecked(enabledByDefault ? !value.startsWith("FALSE", Qt::CaseInsensitive)
                                           : value.startsWith("TRUE", Qt::CaseInsensitive));
        visualForm->addRow(field);
        visualFlags.append(field);
        return field;
    };
    auto *clouds = addVisualFlag("EnableClouds", QObject::tr("Clouds"), true);
    auto *shadows = addVisualFlag("EnableCloudShadows", QObject::tr("Cloud shadows"), false);
    shadows->setEnabled(clouds->isChecked());
    QObject::connect(clouds, &QCheckBox::toggled, shadows, &QWidget::setEnabled);
    addVisualFlag("EnableNightlights", QObject::tr("Planet night lights"), true);
    // Orbiter.cfg uses levels 1 through SURF_MAX_PATCHLEVEL2 (Config.h).
    auto *detail = addNumber(visualForm, "PlanetMaxPatchLevel", QObject::tr("Maximum planet surface detail"), 21, 1, 21, 0);
    detail->setToolTip(QObject::tr("Highest surface tile level Orbiter may use. Available detail depends on the installed planet textures."));
    QComboBox *aspectRatio = nullptr;
    QCheckBox *fullscreen = nullptr, *vsync = nullptr;
    if (profile.native) {
        auto *video = new QWidget;
        auto *videoForm = new QFormLayout(video);
        tabs->addTab(video, QObject::tr("Video"));
#ifdef Q_OS_LINUX
        videoForm->addRow(QObject::tr("Graphics engine"), new QLabel(QObject::tr("OpenGL")));
        fullscreen = new QCheckBox(QObject::tr("Fullscreen on primary display"));
        fullscreen->setObjectName("fullscreen");
        fullscreen->setToolTip(QObject::tr("Use the display’s current resolution and refresh rate."));
        fullscreen->setChecked(assignment(original, "Fullscreen").captured(1).startsWith("TRUE", Qt::CaseInsensitive));
        videoForm->addRow(fullscreen);
        vsync = new QCheckBox(QObject::tr("Vertical sync (VSync)"));
        vsync->setObjectName("vsync");
        vsync->setChecked(!assignment(original, "NoVSync").captured(1).startsWith("TRUE", Qt::CaseInsensitive));
        videoForm->addRow(vsync);
#else
        videoForm->addRow(QObject::tr("Graphics engine"), new QLabel(QObject::tr("OpenGL (windowed)")));
        videoForm->addRow(QObject::tr("Vertical sync"), new QLabel(QObject::tr("On (requested)")));
#endif
        auto *width = addNumber(videoForm, "WindowWidth", QObject::tr("Window width"), 1280, 320, 16384, 0, QObject::tr(" px"));
        auto *height = addNumber(videoForm, "WindowHeight", QObject::tr("Window height"), 720, 200, 16384, 0, QObject::tr(" px"));
        aspectRatio = addAspectRatio(videoForm, width, height);
        if (fullscreen) {
            auto showWindowSize = [=](bool full) {
                videoForm->setRowVisible(width, !full);
                videoForm->setRowVisible(height, !full);
                videoForm->setRowVisible(aspectRatio, !full);
            };
            showWindowSize(fullscreen->isChecked());
            QObject::connect(fullscreen, &QCheckBox::toggled, video, showWindowSize);
        }
    }

    auto *modules = new ModulesPage(profile, original);
    tabs->addTab(modules, QObject::tr("Modules"));

    ExtraPage *extra = nullptr;
#ifdef Q_OS_LINUX
    if (profile.native) {
        extra = new ExtraPage(profile, [&](const QString &key) { return assignment(original, key).captured(1); });
        tabs->addTab(extra, QObject::tr("Extra"));
    }
#endif
    auto values = [&] {
        Values result = extra ? extra->values() : Values{};
        result.insert("UnlimitedFuel", limitedFuel->isChecked() ? "FALSE" : "TRUE");
        for (auto *flag : visualFlags)
            result.insert(flag->objectName(), flag->isChecked() ? "TRUE" : "FALSE");
        if (fullscreen) {
            result.insert("Fullscreen", fullscreen->isChecked() ? "TRUE" : "FALSE");
            result.insert("NoVSync", vsync->isChecked() ? "FALSE" : "TRUE");
        }
        for (auto *field : numericFields)
            result.insert(field->objectName(), QString::number(field->value(), 'f', field->decimals()));
        return result;
    };
    const auto before = values();
    auto *buttons = new QDialogButtonBox(QDialogButtonBox::Save | QDialogButtonBox::Cancel);
    layout->addWidget(buttons);
    QObject::connect(buttons, &QDialogButtonBox::rejected, &dialog, &QDialog::reject);
    QObject::connect(buttons, &QDialogButtonBox::accepted, &dialog, [&] {
        const auto after = values();
        if (extra && stagesChanged(before, after)) {
            const auto error = extra->propagationError();
            if (!error.isEmpty()) {
                QMessageBox::warning(&dialog, dialog.windowTitle(), error);
                return;
            }
        }
        const auto error = saveChanges(path, original, before, after, *modules, profile,
                                      aspectRatio && aspectRatio->currentData().isValid());
        if (error.isEmpty())
            dialog.accept();
        else
            QMessageBox::warning(&dialog, dialog.windowTitle(), error);
    });
    dialog.exec();
}
