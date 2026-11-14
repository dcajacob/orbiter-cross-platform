// Licensed under the MIT License
#pragma once

#include <QString>
#include <optional>

class Keymap;
class QWidget;

QString joystickShortcutName(unsigned shortcut);
QString joystickShortcutAction(const Keymap &keymap, unsigned shortcut);
std::optional<unsigned> editJoystickShortcut(QWidget *parent, const Keymap &keymap,
                                              const QString &buttonName, unsigned shortcut);
