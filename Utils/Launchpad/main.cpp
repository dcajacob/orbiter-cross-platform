#include "Launchpad.h"

#include <QApplication>
#include <QCommandLineParser>
#include <QTimer>

int main(int argc, char **argv)
{
    QApplication app(argc, argv);
    app.setOrganizationName("Orbiter");
    app.setApplicationName("Orbiter Launchpad");
    app.setStyle("Fusion");
    app.setStyleSheet(R"(
        QWidget#launchpad { background: #101925; }
        QDialog#flightSettings, QDialog#orbiterAbout { background: #101925; }
        QDialog#flightSettings QTabWidget::pane, QDialog#orbiterAbout QTabWidget::pane { background: #172433; border: 1px solid #344a60; }
        QDialog#flightSettings QTabBar::tab, QDialog#orbiterAbout QTabBar::tab { background: #21354a; padding: 6px 14px; }
        QDialog#flightSettings QTabBar::tab:selected, QDialog#orbiterAbout QTabBar::tab:selected { background: #2d5475; }
        QDialog#flightSettings QDoubleSpinBox { background: #101925; padding: 4px; }
        QComboBox#windowAspectRatio, QComboBox#windowAspectRatio QAbstractItemView {
            background: #21354a; color: #e5edf6; selection-background-color: #2d5475;
        }
        QTreeWidget#moduleList QHeaderView::section {
            background: #21354a; color: #e5edf6; padding: 4px 6px; border: 0;
        }
        QWidget { color: #e5edf6; font-size: 14px; }
        QLabel#heading { font-size: 28px; font-weight: 600; }
        QLabel#scenarioTitle { font-size: 24px; font-weight: 600; margin: 2px 0; }
        QLabel#scenarioLocation, QLabel#launchStatus { color: #a9bdcf; }
        QLineEdit, QTreeWidget, QTextBrowser, QMenu {
            color: #e5edf6; background: #172433; border: 1px solid #344a60;
            border-radius: 6px; selection-background-color: #2d5475; selection-color: #ffffff;
        }
        QLineEdit { padding: 8px 10px; }
        QLineEdit:focus, QTreeWidget:focus, QTextBrowser:focus { border-color: #72bee9; }
        QTreeWidget { padding: 5px; }
        QTreeWidget::item { min-height: 26px; padding: 1px 3px; }
        QTreeWidget::item:hover { background: #253a50; }
        QTextBrowser { padding: 10px; }
        QTextBrowser#aboutCredits { background: white; color: black; }
        QMenu { padding: 5px; }
        QMenu::item { padding: 7px 12px; }
        QMenu::item:selected { background: #2d5475; }
        QSplitter::handle { background: #334961; }
        QSplitter::handle:hover { background: #72bee9; }
        QPushButton {
            color: #e5edf6; background: #21354a; border: 1px solid #405e77;
            border-radius: 6px; padding: 8px 15px;
        }
        QPushButton:hover { background: #2a465f; }
        QPushButton:focus { border-color: #9cdbff; }
        QPushButton#launchButton { color: #0c2536; background: #8fd5f6; border-color: #8fd5f6; font-weight: 600; }
        QPushButton#launchButton:hover { background: #b3e5fc; }
        QPushButton#launchButton:focus { border-color: #ffffff; }
        QPushButton#launchButton:disabled { color: #9aafbf; background: #283847; border-color: #40556a; }
    )");

    QCommandLineParser parser;
    parser.setApplicationDescription("Browse scenarios and launch Orbiter.");
    parser.addHelpOption();
    parser.addOption({"about", "Open the About Orbiter page."});
    parser.addOption({"profile", "Use a simulator profile.", "json"});
#ifdef Q_OS_LINUX
    parser.addOption({"joystick-setup", "Open the Linux joystick setup dialog."});
#endif
    parser.process(app);
    Launchpad window(parser.value("profile"));
    window.setAttribute(Qt::WA_StyledBackground);
    window.show();
    if (parser.isSet("about"))
        QTimer::singleShot(0, &window, &Launchpad::openAbout);
#ifdef Q_OS_LINUX
    if (parser.isSet("joystick-setup"))
        QTimer::singleShot(0, &window, &Launchpad::openJoystickSetup);
#endif
    return app.exec();
}
