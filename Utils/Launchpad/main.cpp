#include "Launchpad.h"
#include "../ProjectLauncher/RuntimeLibrary.h"
#include "LaunchpadAppearance.h"

#include <QApplication>
#include <QCommandLineParser>
#include <QTimer>

int main(int argc, char **argv)
{
    QApplication app(argc, argv);
    app.setOrganizationName("Orbiter");
    app.setApplicationName("Orbiter Launchpad");
    applyLaunchpadAppearance(app);

    QCommandLineParser parser;
    parser.setApplicationDescription("Browse scenarios and launch Orbiter.");
    parser.addHelpOption();
    parser.addOption({"about", "Open the About Orbiter page."});
    parser.addOption({"profile", "Use a simulator profile.", "json"});
#ifdef Q_OS_LINUX
    parser.addOption({"joystick-setup", "Open the Linux joystick setup dialog."});
#endif
    parser.process(app);
    Launchpad window(parser.value("profile"), standardRuntimeLocations());
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
