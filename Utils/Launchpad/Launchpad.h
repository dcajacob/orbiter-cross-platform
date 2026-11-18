#pragma once

#include "SimulatorProfile.h"

#include <QProcess>
#include <QWidget>

class QCheckBox;
class QLabel;
class QLineEdit;
class QPushButton;
class ScenarioBrowser;
class QTreeWidget;
class QTreeWidgetItem;

class Launchpad : public QWidget {
public:
    explicit Launchpad(const QString &profilePath);
    void openJoystickSetup();
    void openAbout();

protected:
    void closeEvent(QCloseEvent *event) override;

private:
    void loadProfile(const QString &path);
    void useProfile(SimulatorProfile selected);
    void refreshScenarios(const QString &selectedPath = {});
    void addScenarios(const QString &root, QTreeWidgetItem *savedFolder = nullptr);
    void filterScenarios();
    void showSelection();
    void copyScenario();
    void launchScenario();
    void showWindow();

    SimulatorProfile profile;
    QProcess simulator;
    QTreeWidget *scenarios;
    ScenarioBrowser *description;
    QLineEdit *search;
    QCheckBox *paused;
    QPushButton *flightSettings;
    QPushButton *launch;
    QPushButton *copy;
    QPushButton *openLog;
    QLabel *title;
    QLabel *location;
    QLabel *status;
    QString launchLog;
};
