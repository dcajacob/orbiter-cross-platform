#include "RuntimeLibrary.h"
#include "../Launchpad/Launchpad.h"
#include "../Launchpad/LaunchpadAppearance.h"

#include <QApplication>
#include <QCommandLineParser>
#include <QDir>
#include <QIcon>
#include <QTextStream>
#include <memory>

int main(int argc, char **argv)
{
    bool cli = false;
    for (int i = 1; i < argc; ++i) {
        const QByteArray arg(argv[i]);
        if (arg == "--list" || arg == "--help" || arg == "-h" ||
            arg == "--add-location" || arg.startsWith("--add-location="))
            cli = true;
    }
    std::unique_ptr<QCoreApplication> app;
    if (cli)
        app = std::make_unique<QCoreApplication>(argc, argv);
    else
        app = std::make_unique<QApplication>(argc, argv);
    app->setOrganizationName("Orbiter");
    app->setApplicationName("Orbiter Launchpad");

    QCommandLineParser parser;
    parser.setApplicationDescription("Choose an Orbiter runtime and launch a scenario.");
    parser.addHelpOption();
    parser.addOption({"list", "List discovered runtimes without opening a window."});
    parser.addOption({"search", "Also search this installation, directory or Launchpad profile for this session.", "path"});
    parser.addOption({"add-location", "Remember a runtime location for future searches. May be repeated.", "path"});
    parser.process(*app);

    QStringList locations = parser.values("search") + standardRuntimeLocations();
    const auto additions = parser.values("add-location");
    for (const auto &path : additions) {
        if (findOrbiterRuntimes({path}).isEmpty()) {
            QTextStream(stderr) << "No main Orbiter runtime found at " << path << Qt::endl;
            return 1;
        }
    }
    for (const auto &path : additions)
        rememberLocation(path);
    if (parser.isSet("list")) {
        QTextStream out(stdout);
        for (const auto &runtime : findOrbiterRuntimes(QStringList{lastProjectRuntime()} + additions + locations + registeredLocations()))
            out << runtime.name << '\t' << QDir::toNativeSeparators(runtime.path) << Qt::endl;
    }
    if (cli)
        return 0;

    applyLaunchpadAppearance(*static_cast<QApplication *>(app.get()));
    QApplication::setWindowIcon(QIcon(":/launchpad/Icon64.bmp"));
    Launchpad window({}, locations, true);
    window.show();
    return app->exec();
}
