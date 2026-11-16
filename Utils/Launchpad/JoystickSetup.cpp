// Licensed under the MIT License
#include "JoystickSetup.h"
#include "JoystickMapping.h"
#include "JoystickShortcutDialog.h"
#include "Production/NativeJoystick.h"
#include "VelocityOneTouchpad.h"

#include <QCheckBox>
#include <QComboBox>
#include <QDialog>
#include <QDialogButtonBox>
#include <QFile>
#include <QFormLayout>
#include <QHBoxLayout>
#include <QHeaderView>
#include <QLabel>
#include <QMessageBox>
#include <QProgressBar>
#include <QPushButton>
#include <QRegularExpression>
#include <QSaveFile>
#include <QSignalBlocker>
#include <QTabWidget>
#include <QTableWidget>
#include <QTimer>
#include <QVBoxLayout>

#include <sstream>

namespace {
using orbiter::production::JoystickMapping;
using orbiter::production::IsVelocityOnePcMode;
using orbiter::production::VelocityOneTouchpad;
namespace Control {
enum Index { Roll, Pitch, Yaw, Throttle, Alternate, Count };
}

struct Sample {
    QVector<float> axes;
    QVector<unsigned char> buttons;
    QVector<unsigned char> hats;
};

Sample sample(int slot)
{
    Sample result;
    int count = 0;
    if (const auto *axes = glfwGetJoystickAxes(slot, &count))
        result.axes = QVector<float>(axes, axes + count);
    if (const auto *buttons = glfwGetJoystickButtons(slot, &count))
        result.buttons = QVector<unsigned char>(buttons, buttons + count);
    if (const auto *hats = glfwGetJoystickHats(slot, &count))
        result.hats = QVector<unsigned char>(hats, hats + count);
    return result;
}

class JoystickSetup final : public QDialog {
public:
    JoystickSetup(QWidget *parent, const QString &config, const QString &keymapPath)
        : QDialog(parent), configPath(QFile::encodeName(config).constData()),
          initial(JoystickMapping::Read(configPath))
    {
        setWindowTitle(tr("Joystick setup"));
        setObjectName("joystickSetup");
        resize(780, 575);
        if (!keymapPath.isEmpty())
            keymap.Read(QFile::encodeName(keymapPath).constData());
        auto *layout = new QVBoxLayout(this);
        auto *deviceForm = new QFormLayout;
        device->setObjectName("joystickDevice");
        deviceForm->addRow(tr("&Device"), device);
        layout->addLayout(deviceForm);
        hatsStatus->setObjectName("joystickHats");
        hatsStatus->setTextFormat(Qt::PlainText);
        hatsStatus->setWordWrap(true);
        layout->addWidget(hatsStatus);
        auto *lookControls = new QHBoxLayout;
        h1Look->setObjectName("joystickH1Look");
        h2Look->setObjectName("joystickH2Look");
        h1Look->hide();
        h2Look->hide();
        lookControls->addWidget(h1Look);
        lookControls->addWidget(h2Look);
        lookControls->addStretch();
        layout->addLayout(lookControls);
        connect(h1Look, &QCheckBox::toggled, this, &JoystickSetup::updateCameraButtonLabels);
        connect(h2Look, &QCheckBox::toggled, this, &JoystickSetup::updateCameraButtonLabels);

        auto *tabs = new QTabWidget;
        tabs->addTab(axesTable, tr("Axes"));
        tabs->addTab(buttonsTable, tr("Buttons"));
        buttonsTable->setColumnCount(4);
        buttonsTable->setHorizontalHeaderLabels({tr("Button"), tr("Live input"), tr("Shortcut"), tr("Orbiter action")});
        buttonsTable->setColumnWidth(0, 163);
        buttonsTable->setColumnWidth(1, 96);
        buttonsTable->setColumnWidth(2, 190);
        axesTable->setObjectName("joystickAxes");
        buttonsTable->setObjectName("joystickButtons");
        layout->addWidget(tabs, 1);

        auto *form = new QFormLayout;
        const std::array<QString, Control::Count> names{
            tr("Roll"), tr("Pitch"), tr("Yaw / twist"), tr("Main throttle"), tr("Hold to switch roll to yaw")
        };
        for (int i = 0; i < Control::Count; ++i) {
            auto *row = new QHBoxLayout;
            binding[i] = new QComboBox;
            binding[i]->setObjectName(QString("joystickBinding%1").arg(i));
            binding[i]->setAccessibleName(names[i]);
            row->addWidget(binding[i], 1);
            if (i != Control::Alternate) {
                reverse[i] = new QCheckBox(tr("Reverse"));
                reverse[i]->setObjectName(QString("joystickReverse%1").arg(i));
                reverse[i]->setAccessibleName(tr("Reverse %1").arg(names[i]));
                row->addWidget(reverse[i]);
            }
            capture[i] = new QPushButton(tr("Detect…"));
            capture[i]->setObjectName(QString("joystickDetect%1").arg(i));
            capture[i]->setAccessibleName(tr("Detect %1").arg(names[i]));
            connect(capture[i], &QPushButton::clicked, this, [this, i] {
                if (detecting == i)
                    stopCapture();
                else
                    detect(i);
            });
            row->addWidget(capture[i]);
            form->addRow(names[i], row);
        }
        layout->addLayout(form);
        connect(binding[Control::Alternate], &QComboBox::currentIndexChanged, this, &JoystickSetup::updateCameraButtonLabels);

        status->setWordWrap(true);
        status->setObjectName("joystickStatus");
        status->setTextFormat(Qt::PlainText);
        layout->addWidget(status);

        auto *buttons = new QDialogButtonBox(QDialogButtonBox::Save | QDialogButtonBox::Cancel);
        save = buttons->button(QDialogButtonBox::Save);
        auto *defaults = buttons->addButton(tr("Use simulator defaults"), QDialogButtonBox::ResetRole);
        defaults->setEnabled(QFile::exists(QFile::decodeName(JoystickMapping::Path(configPath).c_str())));
        connect(defaults, &QPushButton::clicked, this, [this] {
            std::error_code failure;
            std::filesystem::remove(JoystickMapping::Path(configPath), failure);
            if (failure)
                status->setText(tr("Could not remove the saved mapping."));
            else
                accept();
        });
        connect(buttons, &QDialogButtonBox::accepted, this, &JoystickSetup::saveMapping);
        connect(buttons, &QDialogButtonBox::rejected, this, &QDialog::reject);
        layout->addWidget(buttons);

        connect(device, &QComboBox::currentIndexChanged, this, &JoystickSetup::selectDevice);
        connect(&timer, &QTimer::timeout, this, &JoystickSetup::poll);
        timer.start(35);
        poll();
    }

private:
    static QTableWidget *table(const QString &name)
    {
        auto *view = new QTableWidget(0, 2);
        view->setHorizontalHeaderLabels({name, tr("Live input")});
        view->setEditTriggers(QAbstractItemView::NoEditTriggers);
        view->setSelectionMode(QAbstractItemView::NoSelection);
        view->setColumnWidth(0, 92);
        view->verticalHeader()->hide();
        view->horizontalHeader()->setStretchLastSection(true);
        return view;
    }

    QString currentGuid() const { return device->currentData(Qt::UserRole + 1).toString(); }
    int currentSlot() const { return device->currentIndex() < 0 ? -1 : device->currentData().toInt(); }
    bool velocityOne() const { return IsVelocityOnePcMode(currentGuid().toStdString()); }

    QString axisName(int index) const
    {
        const auto number = tr("Axis %1").arg(index + 1);
        if (velocityOne()) {
            const std::array<QString, 8> labels{tr("Roll"), tr("Pitch"), tr("Twist"), tr("H2 horizontal"),
                tr("H2 vertical"), tr("Flap lever"), tr("Main throttle"), tr("Trim wheel")};
            if (unsigned(index) < labels.size())
                return tr("%1 · %2").arg(number, labels[index]);
        }
        return number;
    }

    QString hatName(int index) const
    {
        return velocityOne() && index == 0 ? tr("H1") : tr("Hat %1").arg(index + 1);
    }

    std::array<QString, 4> directions() const
    {
        return {tr("Up"), tr("Right"), tr("Down"), tr("Left")};
    }

    QString buttonName(int index, const Sample &live) const
    {
        const auto number = tr("Button %1").arg(index + 1);
        const int hatDirection = index - (live.buttons.size() - 4 * live.hats.size());
        if (hatDirection >= 0)
            return tr("%1 · %2 %3").arg(number, hatName(hatDirection / 4), directions()[hatDirection % 4]);
        if (velocityOne()) {
            if (index == 6)
                return tr("%1 · X").arg(number);
            if (index == 14)
                return tr("%1 · Trim wheel click").arg(number);
            if (index == JoystickMapping::VelocityOneH2Click)
                return tr("%1 · H2 click").arg(number);
        }
        return number;
    }

    void poll()
    {
        glfwPollEvents();
        QStringList signature;
        for (int id = GLFW_JOYSTICK_1; id <= GLFW_JOYSTICK_LAST; ++id) {
            const auto *guid = glfwGetJoystickGUID(id);
            if (guid)
                signature.append(QString::number(id) + ':' + QString::fromLatin1(guid));
        }
        if (signature != devices) {
            const auto previousSlot = currentSlot();
            const auto previousGuid = currentGuid();
            devices = signature;
            const QSignalBlocker guard(device);
            device->clear();
            int selected = -1;
            const auto preferred = initial ? initial->ConnectedSlot() : -1;
            for (int id = GLFW_JOYSTICK_1; id <= GLFW_JOYSTICK_LAST; ++id) {
                const auto *guid = glfwGetJoystickGUID(id);
                if (!guid)
                    continue;
                const auto identity = QString::fromLatin1(guid);
                const auto name = QString::fromUtf8(glfwGetJoystickName(id));
                device->addItem(tr("%1  ·  device %2").arg(name).arg(id + 1), id);
                device->setItemData(device->count() - 1, identity, Qt::UserRole + 1);
                if ((id == previousSlot && identity == previousGuid) || (previousGuid.isEmpty() && id == preferred))
                    selected = device->count() - 1;
            }
            const auto untouched = selected >= 0 && device->itemData(selected).toInt() == previousSlot
                && device->itemData(selected, Qt::UserRole + 1).toString() == previousGuid;
            device->setCurrentIndex(selected >= 0 ? selected : device->count() ? 0 : -1);
            if (!untouched)
                selectDevice();
        } else if (currentSlot() >= 0) {
            updateLive(sample(currentSlot()));
        }
        save->setEnabled(currentSlot() >= 0 && axesTable->rowCount() > 0 && detecting < 0);
        if (currentSlot() < 0)
            status->setText(tr("No joystick detected. Plug it in, or switch it to PC mode."));
    }

    void selectDevice()
    {
        ++deviceSelection;
        touchpad.Reset();
        stopCapture();
        const auto slot = currentSlot();
        const auto live = slot >= 0 ? sample(slot) : Sample();
        JoystickMapping map;
        map.guid = currentGuid().toStdString();
        map.alternate = orbiter::production::NativeJoystickAlternateButton(map.guid);
        if (initial && initial->guid == map.guid)
            map = *initial;
        else
            readDefaults(map);
        for (int i = 0; i < Control::Count; ++i) {
            auto *combo = binding[i];
            const bool button = i == Control::Alternate;
            const int count = button ? live.buttons.size() : live.axes.size();
            combo->clear();
            combo->addItem(tr("Disabled"), -1);
            for (int control = 0; control < count; ++control)
                combo->addItem(button ? buttonName(control, live) : axisName(control), control);
            combo->setCurrentIndex(std::max(0, combo->findData(button ? map.alternate : map.axes[i])));
            combo->setEnabled(count > 0);
            if (!button) {
                reverse[i]->setChecked(map.IsReversed(i));
                reverse[i]->setEnabled(count > 0);
            }
            capture[i]->setEnabled(count > 0);
        }
        axesTable->setRowCount(0);
        axesTable->setColumnWidth(0, 176);
        for (int i = 0; i < live.axes.size(); ++i) {
            axesTable->insertRow(i);
            axesTable->setItem(i, 0, new QTableWidgetItem(axisName(i)));
            auto *bar = new QProgressBar;
            bar->setObjectName(QString("joystickAxis%1").arg(i));
            bar->setRange(-1000, 1000);
            axesTable->setCellWidget(i, 1, bar);
        }
        buttonShortcuts = map.buttonKeys;
        touchpadShortcut = map.touchpadKey;
        firstH1Button = -1;
        h1Look->setVisible(velocityOne());
        h2Look->setVisible(velocityOne());
        h1Look->setChecked(map.CameraControls() & JoystickMapping::LookWithH1);
        h2Look->setChecked(map.CameraControls() & JoystickMapping::LookWithH2);
        buttonsTable->setRowCount(0);
        if (velocityOne() && !live.hats.isEmpty() && live.buttons.size() <= int(buttonShortcuts.size()))
            firstH1Button = live.buttons.size() - 4 * live.hats.size();
        touchpadRow = -1;
        for (int i = 0; i < live.buttons.size() && i < int(buttonShortcuts.size()); ++i) {
            addShortcutRow(buttonName(i, live), QString("joystickButtonKey%1").arg(i), buttonShortcuts[i]);
        }
        if (velocityOne()) {
            touchpadRow = buttonsTable->rowCount();
            addShortcutRow(tr("Red touchpad click"), "joystickTouchpadKey", touchpadShortcut);
        }
        updateCameraButtonLabels();
        previousButtons = live.buttons;
        updateLive(live);
    }

    void addShortcutRow(const QString &label, const QString &objectName, unsigned &shortcut)
    {
        const int index = buttonsTable->rowCount();
        buttonsTable->insertRow(index);
        buttonsTable->setItem(index, 0, new QTableWidgetItem(label));
        buttonsTable->setItem(index, 1, new QTableWidgetItem);
        buttonsTable->setItem(index, 3, new QTableWidgetItem);
        auto *key = new QPushButton;
        key->setObjectName(objectName);
        key->setAccessibleName(tr("Shortcut for %1").arg(label));
        buttonsTable->setCellWidget(index, 2, key);
        connect(key, &QPushButton::clicked, this, [this, index, label, &shortcut] {
            const auto selection = deviceSelection;
            const auto updated = editJoystickShortcut(this, keymap, label, shortcut);
            if (updated && selection == deviceSelection) {
                shortcut = *updated;
                updateShortcut(index, shortcut);
            }
        });
        updateShortcut(index, shortcut);
    }

    void updateShortcut(int index, unsigned shortcut)
    {
        auto *button = static_cast<QPushButton *>(buttonsTable->cellWidget(index, 2));
        auto *action = buttonsTable->item(index, 3);
        const bool h1Direction = firstH1Button >= 0 && index >= firstH1Button && index < firstH1Button + 4;
        const bool useDefault = !shortcut && binding[Control::Alternate]->currentData().toInt() != index;
        const bool h1QuickLook = useDefault && h1Direction && h1Look->isChecked();
        const bool h2Recenter = useDefault && velocityOne() && h2Look->isChecked()
            && index == JoystickMapping::VelocityOneH2Click && index != touchpadRow
            && (firstH1Button < 0 || index < firstH1Button);
        const auto name = h1QuickLook || h2Recenter ? tr("Default") : joystickShortcutName(shortcut);
        button->setText(name);
        button->setToolTip(name);
        auto description = joystickShortcutAction(keymap, shortcut);
        if (h1QuickLook)
            description = tr("Quick look %1 (hold)").arg(directions()[index - firstH1Button].toLower());
        else if (h2Recenter)
            description = tr("Recenter cockpit view");
        action->setText(description);
        action->setToolTip(description);
    }

    void updateCameraButtonLabels()
    {
        if (firstH1Button >= 0)
            for (int index = firstH1Button; index < firstH1Button + 4 && index < buttonsTable->rowCount(); ++index)
                updateShortcut(index, buttonShortcuts[index]);
        const int h2Click = JoystickMapping::VelocityOneH2Click;
        if (velocityOne() && h2Click < buttonsTable->rowCount() && h2Click != touchpadRow)
            updateShortcut(h2Click, buttonShortcuts[h2Click]);
    }

    void readDefaults(JoystickMapping &map) const
    {
        QFile config(QFile::decodeName(configPath.c_str()));
        if (!config.open(QIODevice::ReadOnly))
            return;
        const auto bytes = QString::fromUtf8(config.readAll());
        const auto setting = [&bytes](const QString &key) {
            const QRegularExpression pattern("^" + key + "[ \\t]*=[ \\t]*([^;\\r\\n]*)",
                                             QRegularExpression::MultilineOption);
            return pattern.match(bytes).captured(1).trimmed();
        };
        bool ok = false;
        const int yaw = setting("NativeJoystickRudderAxis").toInt(&ok);
        if (ok && yaw >= -1 && yaw <= 15)
            map.axes[Control::Yaw] = yaw;
        const int throttle = setting("NativeJoystickThrottleAxis").toInt(&ok);
        map.axes[Control::Throttle] = orbiter::production::NativeThrottleAxis(
            setting("JoystickThrottleAxis").toUInt(), ok && throttle >= -2 && throttle <= 15 ? throttle : -2);
        if (setting("NativeJoystickThrottleInverted").compare("TRUE", Qt::CaseInsensitive) == 0)
            map.reversed |= 1u << Control::Throttle;
    }

    void detect(int control)
    {
        stopCapture();
        detecting = control;
        baseline = sample(currentSlot());
        capture[control]->setText(tr("Cancel"));
        save->setEnabled(false);
        status->setText(control == Control::Alternate ? tr("Press the button you want to use.")
            : control == Control::Throttle ? tr("Move the throttle from idle toward full power.")
            : control == Control::Pitch ? tr("Pull back on the stick.")
            : tr("Move the control to the right."));
    }

    void stopCapture()
    {
        if (detecting >= 0) {
            capture[detecting]->setText(tr("Detect…"));
            detecting = -1;
        }
        status->setText(tr("Move a control to see its input, or use Detect to bind it."));
    }

    void updateLive(const Sample &live)
    {
        QStringList hats;
        const auto names = directions();
        for (int i = 0; i < live.hats.size(); ++i) {
            QStringList active;
            for (unsigned direction = 0; direction < names.size(); ++direction)
                if (live.hats[i] & (1u << direction))
                    active.append(names[direction]);
            hats.append(tr("%1: %2").arg(hatName(i), active.isEmpty() ? tr("Centered") : active.join(" + ")));
        }
        hatsStatus->setVisible(!hats.isEmpty());
        const auto hatText = hats.join("    ");
        if (hatsStatus->text() != hatText)
            hatsStatus->setText(hatText);
        for (int i = 0; i < axesTable->rowCount() && i < live.axes.size(); ++i) {
            auto *bar = static_cast<QProgressBar *>(axesTable->cellWidget(i, 1));
            const auto value = std::isfinite(live.axes[i]) ? std::clamp(live.axes[i], -1.f, 1.f) : 0.f;
            const int scaled = std::lround(value * 1000);
            if (scaled != bar->value()) {
                bar->setFormat(QString::number(value, 'f', 3));
                bar->setValue(scaled);
            }
        }
        int pressedRow = -1;
        for (int i = 0; i < buttonsTable->rowCount() && i < live.buttons.size(); ++i) {
            auto *item = buttonsTable->item(i, 1);
            const auto state = live.buttons[i] ? tr("Pressed") : tr("Released");
            if (item->text() != state)
                item->setText(state);
            if (live.buttons[i] && i < previousButtons.size() && !previousButtons[i])
                pressedRow = i;
        }
        previousButtons = live.buttons;
        if (touchpadRow >= 0) {
            const auto state = touchpad.Poll();
            auto *item = buttonsTable->item(touchpadRow, 1);
            const auto text = state.access == VelocityOneTouchpad::Access::Denied ? tr("Needs access")
                : state.access == VelocityOneTouchpad::Access::Unavailable ? tr("Unavailable")
                : state.pressed || state.down ? tr("Pressed") : tr("Released");
            if (item->text() != text)
                item->setText(text);
            item->setToolTip(state.access == VelocityOneTouchpad::Access::Denied
                ? tr("Linux exposes this click as a separate mouse. See the Launchpad README for device access.")
                : QString());
            if (state.pressed)
                pressedRow = touchpadRow;
        }
        if (pressedRow >= 0 && buttonsTable->isVisible())
            buttonsTable->scrollToItem(buttonsTable->item(pressedRow, 0), QAbstractItemView::EnsureVisible);

        if (detecting < 0)
            return;
        int index = -1;
        if (detecting == Control::Alternate) {
            for (int i = 0; i < baseline.buttons.size() && i < live.buttons.size(); ++i) {
                if (live.buttons[i] && !baseline.buttons[i]) {
                    index = i;
                    break;
                }
                baseline.buttons[i] = live.buttons[i];
            }
        } else {
            float strongest = 0.35f;
            for (int i = 0; i < baseline.axes.size() && i < live.axes.size(); ++i) {
                const float delta = live.axes[i] - baseline.axes[i];
                if (std::abs(delta) > std::abs(strongest)) {
                    strongest = delta;
                    index = i;
                }
            }
            if (index >= 0)
                reverse[detecting]->setChecked(detecting == Control::Throttle ? strongest > 0 : strongest < 0);
        }
        if (index >= 0) {
            const auto *combo = binding[detecting];
            binding[detecting]->setCurrentIndex(combo->findData(index));
            stopCapture();
            status->setText(tr("Detected %1.").arg(combo->currentText()));
        }
    }

    void saveMapping()
    {
        JoystickMapping mapping;
        mapping.guid = currentGuid().toStdString();
        mapping.slot = currentSlot();
        const auto *connectedGuid = mapping.slot >= 0 ? glfwGetJoystickGUID(mapping.slot) : nullptr;
        if (!connectedGuid || mapping.guid != connectedGuid)
            return;
        for (int i = 0; i < Control::Alternate; ++i) {
            mapping.axes[i] = binding[i]->currentData().toInt();
            if (mapping.axes[i] >= 0 && std::count(mapping.axes.begin(), mapping.axes.begin() + i, mapping.axes[i])) {
                status->setText(tr("Choose a different axis for each mapped flight control."));
                return;
            }
            if (reverse[i]->isChecked())
                mapping.reversed |= 1u << i;
        }
        mapping.alternate = binding[Control::Alternate]->currentData().toInt();
        mapping.buttonKeys = buttonShortcuts;
        mapping.touchpadKey = touchpadShortcut;
        if (velocityOne())
            mapping.cameraControls = (h1Look->isChecked() ? JoystickMapping::LookWithH1 : 0)
                | (h2Look->isChecked() ? JoystickMapping::LookWithH2 : 0);
        std::ostringstream stream;
        mapping.Write(stream);
        const auto bytes = QByteArray::fromStdString(stream.str());
        QSaveFile file(QFile::decodeName(JoystickMapping::Path(configPath).c_str()));
        if (!file.open(QIODevice::WriteOnly) || file.write(bytes) != bytes.size() || !file.commit()) {
            status->setText(tr("Could not save the mapping: %1").arg(file.errorString()));
            return;
        }
        accept();
    }

    std::filesystem::path configPath;
    std::optional<JoystickMapping> initial;
    Keymap keymap;
    decltype(JoystickMapping::buttonKeys) buttonShortcuts{};
    VelocityOneTouchpad touchpad;
    unsigned touchpadShortcut = 0;
    int touchpadRow = -1;
    int firstH1Button = -1;
    unsigned deviceSelection = 0;
    QStringList devices;
    QComboBox *device = new QComboBox;
    QTableWidget *axesTable = table(tr("Axis"));
    QTableWidget *buttonsTable = table(tr("Button"));
    QLabel *status = new QLabel;
    QLabel *hatsStatus = new QLabel;
    QCheckBox *h1Look = new QCheckBox(tr("H1 quick look"));
    QCheckBox *h2Look = new QCheckBox(tr("H2 continuous look"));
    QPushButton *save = nullptr;
    std::array<QComboBox *, Control::Count> binding{};
    std::array<QPushButton *, Control::Count> capture{};
    std::array<QCheckBox *, Control::Alternate> reverse{};
    QTimer timer;
    int detecting = -1;
    Sample baseline;
    QVector<unsigned char> previousButtons;
};
}

void showJoystickSetup(QWidget *parent, const QString &config, const QString &keymap)
{
    // Qt owns the actual windows. GLFW only needs a display connection to
    // enumerate and poll the same raw devices as the Linux simulator.
    glfwInitHint(GLFW_PLATFORM, GLFW_ANY_PLATFORM);
    if (!glfwInit()) {
        const char *error = nullptr;
        glfwGetError(&error);
        QMessageBox::warning(parent, QObject::tr("Joystick setup"),
                             QObject::tr("Could not start joystick discovery: %1")
                                 .arg(error ? QString::fromUtf8(error) : QObject::tr("Display connection failed")));
        return;
    }
    {
        JoystickSetup dialog(parent, config, keymap);
        dialog.exec();
    }
    glfwTerminate();
}
