// Licensed under the MIT License
#include <QApplication>
#include <QFile>
#include <QLabel>
#include <QLineEdit>
#include <QPushButton>
#include <QSettings>
#include <QTimer>
#include <QTreeWidget>

namespace {
void receipt(const char* event)
{
    QFile file(qEnvironmentVariable("ORBITER_LAUNCHPAD_TEST_RECEIPT"));
    if (file.open(QIODevice::WriteOnly | QIODevice::Append | QIODevice::Text)) {
        file.write(event);
        file.write("\n");
    }
}

void startProbe()
{
    const auto settings = qEnvironmentVariable("ORBITER_LAUNCHPAD_TEST_SETTINGS");
    if (settings.isEmpty()) return;
    QSettings::setDefaultFormat(QSettings::IniFormat);
    QSettings::setPath(QSettings::IniFormat, QSettings::UserScope, settings);
    QTimer::singleShot(0, [] {
        QWidget* window = nullptr;
        for (auto* candidate : QApplication::topLevelWidgets())
            if (candidate->objectName() == "launchpad") window = candidate;
        if (!window || !window->isVisible()) {
            receipt("launcher-missing");
            QCoreApplication::exit(41);
            return;
        }

        auto* search = window->findChild<QLineEdit*>("scenarioSearch");
        auto* tree = window->findChild<QTreeWidget*>("scenarioTree");
        auto* launch = window->findChild<QPushButton*>("launchButton");
        auto* status = window->findChild<QLabel*>("launchStatus");
        if (!search || !tree || !launch || !status) {
            receipt("launcher-controls-missing");
            QCoreApplication::exit(42);
            return;
        }
        const QString name = "DG Mk4 in orbit";
        search->setText(name);
        const auto matches = tree->findItems(name, Qt::MatchExactly | Qt::MatchRecursive);
        if (matches.size() != 1 || matches.front()->isHidden()) {
            receipt("scenario-search-failed");
            QCoreApplication::exit(43);
            return;
        }
        tree->setCurrentItem(matches.front());
        if (!launch->isEnabled()) {
            receipt("launch-disabled");
            QCoreApplication::exit(44);
            return;
        }

        auto* timer = new QTimer(window);
        timer->setInterval(20);
        QObject::connect(timer, &QTimer::timeout, window,
            [window, tree, launch, status, name, hidden = false]() mutable {
                if (!window->isVisible() && !hidden) {
                    receipt("launcher-hidden-during-flight");
                    hidden = true;
                }
                if (!window->isVisible()) return;
                const QString message = status->text();
                if (message.startsWith("Orbiter could not start") || message.startsWith("Orbiter exited with code")
                    || message == "Orbiter closed unexpectedly.") {
                    receipt(qPrintable(message));
                    QCoreApplication::exit(47);
                    return;
                }
                if (message != QStringLiteral("Session ended.")) return;
                if (!hidden || !tree->currentItem() || tree->currentItem()->text(0) != name || !launch->isEnabled()) {
                    receipt("return-state-invalid");
                    QCoreApplication::exit(45);
                    return;
                }
                receipt("launcher-returned-with-selection");
                QCoreApplication::quit();
            });
        receipt("selected-and-launched-stock-scenario");
        timer->start();
        launch->click();
    });
    QTimer::singleShot(85000, [] {
        receipt("launcher-timeout");
        QCoreApplication::exit(46);
    });
}
}
Q_COREAPP_STARTUP_FUNCTION(startProbe)
