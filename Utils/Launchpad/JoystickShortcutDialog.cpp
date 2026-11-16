// Licensed under the MIT License
#include "JoystickShortcutDialog.h"
#include "JoystickMapping.h"

#include <QComboBox>
#include <QCoreApplication>
#include <QDialog>
#include <QDialogButtonBox>
#include <QFormLayout>
#include <QLabel>
#include <QSet>
#include <QStringList>
#include <QVBoxLayout>
#include <algorithm>

namespace {
using orbiter::production::JoystickModifierKeys;

QString tr(const char *text)
{
    return QCoreApplication::translate("JoystickShortcutDialog", text);
}

QString keyName(unsigned key)
{
    if (key >= OAPI_KEY_F1 && key <= OAPI_KEY_F10)
        return tr("F%1").arg(key - OAPI_KEY_F1 + 1);
    if (key == OAPI_KEY_F11 || key == OAPI_KEY_F12)
        return tr("F%1").arg(key - OAPI_KEY_F11 + 11);
    const auto *name = Keymap::KeyName(key);
    if (!name)
        return {};
    const auto token = QString::fromLatin1(name);
    if (token.startsWith("NUMPAD"))
        return tr("Num %1").arg(token.mid(6) == "ENTER" ? tr("Enter") : token.mid(6));
    switch (key) {
    case OAPI_KEY_ESCAPE: return tr("Esc");
    case OAPI_KEY_BACK: return tr("Backspace");
    case OAPI_KEY_RETURN: return tr("Enter");
    case OAPI_KEY_SPACE: return tr("Space");
    case OAPI_KEY_PRIOR: return tr("Page Up");
    case OAPI_KEY_NEXT: return tr("Page Down");
    case OAPI_KEY_SYSRQ: return tr("Print Screen");
    case OAPI_KEY_CAPITAL: return tr("Caps Lock");
    case OAPI_KEY_NUMLOCK: return tr("Num Lock");
    case OAPI_KEY_SCROLL: return tr("Scroll Lock");
    case OAPI_KEY_ADD: return tr("Num +");
    case OAPI_KEY_SUBTRACT: return tr("Num -");
    case OAPI_KEY_MULTIPLY: return tr("Num *");
    case OAPI_KEY_DIVIDE: return tr("Num /");
    case OAPI_KEY_DECIMAL: return tr("Num .");
    case OAPI_KEY_MINUS: return "-";
    case OAPI_KEY_EQUALS: return "=";
    case OAPI_KEY_LBRACKET: return "[";
    case OAPI_KEY_RBRACKET: return "]";
    case OAPI_KEY_BACKSLASH: return "\\";
    case OAPI_KEY_SEMICOLON: return ";";
    case OAPI_KEY_APOSTROPHE: return "'";
    case OAPI_KEY_GRAVE: return "`";
    case OAPI_KEY_COMMA: return ",";
    case OAPI_KEY_PERIOD: return ".";
    case OAPI_KEY_SLASH: return "/";
    default: return token.left(1) + token.mid(1).toLower();
    }
}

struct Modifier {
    unsigned either;
    unsigned left;
    unsigned right;
    const char *name;
};

constexpr std::array<Modifier, 3> modifiers{{
    {KMOD_CTRL, KMOD_LCTRL, KMOD_RCTRL, "Ctrl"},
    {KMOD_ALT, KMOD_LALT, KMOD_RALT, "Alt"},
    {KMOD_SHIFT, KMOD_LSHIFT, KMOD_RSHIFT, "Shift"}
}};

// Stock vessel bindings are handled by the vessel modules, outside Keymap.
constexpr struct {
    unsigned shortcut;
    const char *description;
} vesselShortcuts[] = {
    {OAPI_KEY_G, "Toggle landing gear (Delta-glider or Atlantis)"},
    {OAPI_KEY_K, "Toggle nose cone (Delta-glider) or payload bay doors (Atlantis)"},
    {OAPI_KEY_B, "Extend airbrake (Delta-glider)"},
    {OAPI_KEY_B | KMOD_CTRL, "Retract airbrake (Delta-glider) or toggle speedbrake (Atlantis)"},
    {OAPI_KEY_D, "Toggle radiator (Delta-glider)"},
    {OAPI_KEY_O, "Toggle outer airlock door (Delta-glider)"},
    {OAPI_KEY_O | KMOD_CTRL, "Toggle inner airlock door (Delta-glider)"},
    {OAPI_KEY_U, "Toggle top hatch (Delta-glider)"},
    {OAPI_KEY_U | KMOD_CTRL, "Toggle top hatch (Delta-glider) or Ku-band antenna (Atlantis)"},
    {OAPI_KEY_SPACE | KMOD_CTRL, "Open vessel controls (Delta-glider) or robotic arm controls (Atlantis)"},
    {OAPI_KEY_J, "Separate the current stage (Atlantis)"},
    {OAPI_KEY_8, "Grapple or release payload (Atlantis)"},
    {OAPI_KEY_9, "Center robotic arm (Atlantis)"},
    {OAPI_KEY_E, "Request an EVA (Atlantis)"}
};

unsigned eitherSide(unsigned shortcut)
{
    for (const auto &modifier : modifiers)
        if (shortcut & modifier.either)
            shortcut |= modifier.either;
    return shortcut;
}

bool matches(const Keymap &keymap, unsigned shortcut, int action)
{
    std::array<char, 256> keys{};
    for (auto modifier : JoystickModifierKeys(shortcut))
        if (modifier)
            keys[modifier] = char(0x80);
    keys[shortcut & 255] = char(0x80);
    return keymap.IsLogicalKey(keys.data(), action);
}
}

QString joystickShortcutName(unsigned shortcut)
{
    if (!shortcut)
        return tr("Unassigned");
    QStringList keys;
    for (const auto &modifier : modifiers) {
        const auto bits = shortcut & modifier.either;
        if (bits == modifier.either)
            keys.append(tr(modifier.name));
        else if (bits)
            keys.append((bits == modifier.left ? tr("Left %1") : tr("Right %1")).arg(tr(modifier.name)));
    }
    const auto name = keyName(shortcut & 255);
    keys.append(name.isEmpty() ? tr("Key %1").arg(shortcut & 255) : name);
    return keys.join('+');
}

QString joystickShortcutAction(const Keymap &keymap, unsigned shortcut)
{
    if (!shortcut)
        return {};
    if ((shortcut & 255) == OAPI_KEY_ESCAPE)
        return tr("Exit simulation");
    // These shortcuts are handled directly by the native session.
    if (shortcut == OAPI_KEY_SPACE || matches(keymap, shortcut, OAPI_LKEY_Pause))
        return tr("Pause or resume simulation");
    if (matches(keymap, shortcut, OAPI_LKEY_Quicksave))
        return tr("Quicksave");
    if ((shortcut & 255) == OAPI_KEY_F5 && !(shortcut & KMOD_CTRL))
        return tr("Reload quicksave");
    if (shortcut == OAPI_KEY_F7)
        return tr("Open scenario editor");
    QStringList actions;
    for (int i = 0; i < LKEY_COUNT; ++i) {
        if (matches(keymap, shortcut, i)) {
            const auto description = i == OAPI_LKEY_DlgCapture
                ? tr("Open screen capture dialog (Windows)") : tr(Keymap::ActionDescription(i));
            if (!actions.contains(description))
                actions.append(description);
        }
    }
    for (const auto &binding : vesselShortcuts)
        if (eitherSide(shortcut) == binding.shortcut)
            actions.append(tr(binding.description));
    if (actions.isEmpty() && (shortcut & KMOD_SHIFT) && !(shortcut & (KMOD_CTRL | KMOD_ALT)))
        return (shortcut & KMOD_SHIFT) == KMOD_RSHIFT
            ? tr("Send key to right MFD (action depends on mode)")
            : tr("Send key to left MFD (action depends on mode)");
    return actions.isEmpty() ? tr("No action in the active keymap (may depend on vessel or panel)")
                             : actions.join(tr(" / "));
}

std::optional<unsigned> editJoystickShortcut(QWidget *parent, const Keymap &keymap,
                                             const QString &buttonName, unsigned shortcut)
{
    QDialog dialog(parent);
    dialog.setWindowTitle(tr("Shortcut for %1").arg(buttonName));
    dialog.setObjectName("joystickShortcut");
    dialog.resize(620, 0);
    auto *layout = new QVBoxLayout(&dialog);
    auto *form = new QFormLayout;
    layout->addLayout(form);

    auto *preset = new QComboBox;
    preset->setObjectName("joystickActionPreset");
    preset->setMaxVisibleItems(15);
    preset->addItem(tr("Choose an Orbiter action…"));
    QSet<unsigned> shortcuts{OAPI_KEY_ESCAPE, OAPI_KEY_SPACE, OAPI_KEY_F5, OAPI_KEY_F7};
    for (int i = 0; i < LKEY_COUNT; ++i)
        if (const auto key = keymap.Binding(i); orbiter::production::IsJoystickShortcut(key))
            shortcuts.insert(key);
    for (const auto &binding : vesselShortcuts)
        shortcuts.insert(binding.shortcut);
    QList<QPair<QString, unsigned>> choices;
    for (unsigned key : shortcuts)
        choices.append({tr("%1 (%2)").arg(joystickShortcutAction(keymap, key), joystickShortcutName(key)), key});
    std::sort(choices.begin(), choices.end(), [](const auto &left, const auto &right) {
        return QString::localeAwareCompare(left.first, right.first) < 0;
    });
    for (const auto &[label, value] : choices)
        preset->addItem(label, value);
    preset->setSizeAdjustPolicy(QComboBox::AdjustToMinimumContentsLengthWithIcon);
    preset->setMinimumContentsLength(22);
    form->addRow(tr("&Orbiter action"), preset);

    auto *key = new QComboBox;
    key->setObjectName("joystickShortcutKey");
    key->addItem(tr("Unassigned"), 0);
    QList<QPair<QString, unsigned>> keys;
    for (unsigned code = 1; code < 256; ++code)
        if (const auto name = keyName(code); !name.isEmpty())
            keys.append({name, code});
    for (const auto &[label, code] : keys)
        key->addItem(label, code);
    form->addRow(tr("&Key"), key);
    std::array<QComboBox *, modifiers.size()> modifierChoices{};
    for (unsigned i = 0; i < modifiers.size(); ++i) {
        const auto &modifier = modifiers[i];
        const auto name = tr(modifier.name);
        auto *combo = modifierChoices[i] = new QComboBox;
        combo->setObjectName("joystickShortcut" + QString::fromLatin1(modifier.name));
        combo->addItem(tr("Off"), 0);
        combo->addItem(tr("Either side"), modifier.either);
        combo->addItem(tr("Left"), modifier.left);
        combo->addItem(tr("Right"), modifier.right);
        form->addRow(name, combo);
    }

    auto *description = new QLabel;
    description->setObjectName("joystickShortcutAction");
    description->setTextFormat(Qt::PlainText);
    description->setWordWrap(true);
    form->addRow(tr("In Orbiter"), description);
    const auto currentShortcut = [&] {
        unsigned value = key->currentData().toUInt();
        if (value)
            for (const auto *combo : modifierChoices)
                value |= combo->currentData().toUInt();
        return value;
    };
    const auto update = [&] {
        const auto mapped = currentShortcut();
        for (auto *combo : modifierChoices)
            combo->setEnabled(mapped != 0);
        description->setText(joystickShortcutAction(keymap, mapped));
    };
    const auto setShortcut = [&](unsigned mapped) {
        key->setCurrentIndex(std::max(0, key->findData(mapped & 255)));
        for (unsigned i = 0; i < modifiers.size(); ++i)
            modifierChoices[i]->setCurrentIndex(modifierChoices[i]->findData(mapped & modifiers[i].either));
        update();
    };

    QObject::connect(key, &QComboBox::currentIndexChanged, &dialog, update);
    for (auto *combo : modifierChoices)
        QObject::connect(combo, &QComboBox::currentIndexChanged, &dialog, update);
    QObject::connect(preset, &QComboBox::activated, &dialog, [&](int index) {
        if (index > 0)
            setShortcut(preset->itemData(index).toUInt());
    });
    setShortcut(shortcut);

    auto *buttons = new QDialogButtonBox(QDialogButtonBox::Ok | QDialogButtonBox::Cancel);
    QObject::connect(buttons, &QDialogButtonBox::accepted, &dialog, &QDialog::accept);
    QObject::connect(buttons, &QDialogButtonBox::rejected, &dialog, &QDialog::reject);
    layout->addWidget(buttons);
    if (dialog.exec() != QDialog::Accepted)
        return {};
    return currentShortcut();
}
