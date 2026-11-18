#pragma once

#include <QMap>
#include <QWidget>

class QTreeWidget;
class QTreeWidgetItem;
struct SimulatorProfile;

class ModulesPage : public QWidget {
public:
    ModulesPage(const SimulatorProfile &profile, const QString &config);

    QMap<QString, bool> startupChanges() const;
    static QString applyStartupChanges(QString &config, const QMap<QString, bool> &changes);
    bool soundChanged() const;
    bool soundChecked() const;

private:
    QTreeWidget *list;
    QTreeWidgetItem *sound = nullptr;
    bool originalSound = false;
};
