#include "Launchpad.h"

#include <QCheckBox>
#include <QCloseEvent>
#include <QDesktopServices>
#include <QDirIterator>
#include <QFile>
#include <QFileDialog>
#include <QFileInfo>
#include <QHBoxLayout>
#include <QLabel>
#include <QLineEdit>
#include <QMap>
#include <QMenu>
#include <QPushButton>
#include <QSettings>
#include <QShortcut>
#include <QSplitter>
#include <QStyle>
#include <QTextBrowser>
#include <QTreeWidget>
#include <QTreeWidgetItemIterator>
#include <QUrl>
#include <QVBoxLayout>

#include <exception>

namespace {
constexpr int DescriptionRole = Qt::UserRole;
constexpr int ScenarioRole = Qt::UserRole + 1;

// Scenario descriptions may refer to arbitrary resources. Use the original text
// and formatting without fetching external pages, style sheets, or images.
class ScenarioBrowser : public QTextBrowser {
    QVariant loadResource(int, const QUrl &) override { return {}; }
};

QString readDescription(const QString &path, const QString &helpRoot, bool folder)
{
    QFile file(path);
    if (!file.open(QIODevice::ReadOnly))
        return {};
    const auto source = QString::fromUtf8(file.read(256 * 1024));
    const QStringList lines = source.split('\n');
    QString kind;
    QStringList body;
    for (const auto &line : lines) {
        const auto token = line.trimmed();
        if (kind.isEmpty()) {
            if (token == "BEGIN_DESC" || token == "BEGIN_HYPERDESC" || token == "BEGIN_URLDESC")
                kind = token.mid(6);
            else if (token.startsWith("BEGIN_"))
                break;
        } else if (token == "END_" + kind) {
            const auto content = body.join('\n').trimmed();
            if (kind == "HYPERDESC")
                return content;
            if (kind == "DESC")
                return "<p>" + content.toHtmlEscaped().replace('\n', "<br>") + "</p>";

            auto parts = content.split(',');
            if (parts.size() != 2 || helpRoot.isEmpty())
                break;
            auto book = parts[0].trimmed().replace('\\', '/');
            const QDir base(helpRoot);
            const auto help = QFileInfo(base.filePath(book + '/' + parts[1].trimmed() + ".htm")).canonicalFilePath();
            const auto root = QFileInfo(helpRoot).canonicalFilePath();
            if (root.isEmpty() || !help.startsWith(root + '/'))
                break;
            QFile page(help);
            if (page.open(QIODevice::ReadOnly))
                return QString::fromUtf8(page.read(256 * 1024));
            break;
        } else {
            body.append(line);
        }
    }
    if (kind.isEmpty() && folder)
        return "<p>" + source.toHtmlEscaped().replace('\n', "<br>") + "</p>";
    return {};
}

bool filterItem(QTreeWidgetItem *item, const QString &query, bool ancestorMatches)
{
    const bool matches = ancestorMatches || item->text(0).contains(query, Qt::CaseInsensitive);
    bool childMatches = false;
    for (int i = 0; i < item->childCount(); ++i)
        childMatches = filterItem(item->child(i), query, matches) || childMatches;
    item->setHidden(!matches && !childMatches);
    if (!query.isEmpty() && (matches || childMatches))
        item->setExpanded(true);
    return matches || childMatches;
}
}

Launchpad::Launchpad(const QString &profilePath)
{
    setWindowTitle(tr("Orbiter Launchpad"));
    setObjectName("launchpad");
    resize(1000, 680);
    setMinimumSize(690, 440);

    auto *outer = new QVBoxLayout(this);
    outer->setContentsMargins(24, 22, 24, 18);
    outer->setSpacing(16);

    auto *header = new QHBoxLayout;
    auto *heading = new QLabel(tr("Orbiter Launchpad"));
    heading->setObjectName("heading");
    header->addWidget(heading);
    header->addStretch();
    auto *setup = new QPushButton(tr("Setup"));
    auto *setupMenu = new QMenu(setup);
    setupMenu->addAction(tr("Open simulator profile…"), this, [this] {
        const auto path = QFileDialog::getOpenFileName(this, tr("Open simulator profile"), {}, tr("JSON profiles (*.json)"));
        if (!path.isEmpty())
            loadProfile(path);
    });
#ifdef Q_OS_WIN
    setupMenu->addAction(tr("Choose Orbiter.exe…"), this, [this] {
        const auto path = QFileDialog::getOpenFileName(this, tr("Choose Orbiter executable"), {},
                                                       tr("Orbiter executable (Orbiter.exe)"));
        if (path.isEmpty())
            return;
        useProfile(SimulatorProfile::fromWindowsExecutable(path));
        QSettings settings;
        settings.remove("simulator/profile");
        settings.setValue("simulator/windowsExecutable", path);
    });
    setupMenu->addAction(tr("Open classic Launchpad"), this, [this] {
        const auto error = profile.validationError();
        if (!error.isEmpty()) {
            status->setText(error);
            return;
        }
        if (profile.native) {
            status->setText(tr("Choose a Windows installation to open its classic Launchpad."));
            return;
        }
        if (QProcess::startDetached(profile.executable, {}, profile.workingDirectory))
            close();
        else
            status->setText(tr("Could not open the classic Launchpad."));
    });
#endif
    setupMenu->addAction(tr("Refresh scenarios"), this, [this] {
        const auto *item = scenarios->currentItem();
        refreshScenarios(item ? item->data(0, ScenarioRole).toString() : QString());
    });
    setup->setMenu(setupMenu);
    header->addWidget(setup);
    outer->addLayout(header);

    auto *splitter = new QSplitter;
    splitter->setChildrenCollapsible(false);
    auto *left = new QWidget;
    auto *leftLayout = new QVBoxLayout(left);
    leftLayout->setContentsMargins(0, 0, 8, 0);
    leftLayout->setSpacing(8);
    search = new QLineEdit;
    search->setObjectName("scenarioSearch");
    search->setPlaceholderText(tr("Search scenarios"));
    search->setAccessibleName(tr("Search scenarios"));
    search->setClearButtonEnabled(true);
    leftLayout->addWidget(search);

    scenarios = new QTreeWidget;
    scenarios->setObjectName("scenarioTree");
    scenarios->setAccessibleName(tr("Scenarios"));
    scenarios->setHeaderHidden(true);
    scenarios->setAnimated(false);
    scenarios->setUniformRowHeights(true);
    leftLayout->addWidget(scenarios);
    splitter->addWidget(left);

    auto *right = new QWidget;
    auto *rightLayout = new QVBoxLayout(right);
    rightLayout->setContentsMargins(8, 0, 0, 0);
    rightLayout->setSpacing(8);
    title = new QLabel;
    title->setObjectName("scenarioTitle");
    title->setTextFormat(Qt::PlainText);
    title->setWordWrap(true);
    location = new QLabel;
    location->setObjectName("scenarioLocation");
    location->setTextFormat(Qt::PlainText);
    location->setWordWrap(true);
    description = new ScenarioBrowser;
    description->setObjectName("scenarioDescription");
    description->setAccessibleName(tr("Scenario description"));
    description->setOpenLinks(false);
    rightLayout->addWidget(title);
    rightLayout->addWidget(location);
    rightLayout->addWidget(description, 1);
    splitter->addWidget(right);
    splitter->setSizes({330, 600});
    splitter->setStretchFactor(1, 1);
    outer->addWidget(splitter, 1);

    auto *footer = new QHBoxLayout;
    status = new QLabel;
    status->setObjectName("launchStatus");
    status->setTextFormat(Qt::PlainText);
    status->setWordWrap(true);
    openLog = new QPushButton(tr("Open log"));
    openLog->hide();
    paused = new QCheckBox(tr("Start paused"));
    launch = new QPushButton(tr("Launch Orbiter"));
    launch->setObjectName("launchButton");
    launch->setEnabled(false);
    footer->addWidget(status, 1);
    footer->addWidget(openLog);
    footer->addWidget(paused);
    footer->addSpacing(6);
    footer->addWidget(launch);
    outer->addLayout(footer);

    connect(search, &QLineEdit::textChanged, this, &Launchpad::filterScenarios);
    auto *find = new QShortcut(QKeySequence::Find, this);
    connect(find, &QShortcut::activated, search, [this] {
        search->setFocus();
        search->selectAll();
    });
    connect(scenarios, &QTreeWidget::currentItemChanged, this, &Launchpad::showSelection);
    connect(scenarios, &QTreeWidget::itemActivated, this, [this](QTreeWidgetItem *item, int) {
        if (item && !item->data(0, ScenarioRole).toString().isEmpty())
            launchScenario();
    });
    connect(launch, &QPushButton::clicked, this, &Launchpad::launchScenario);
    connect(openLog, &QPushButton::clicked, this, [this] {
        if (!QDesktopServices::openUrl(QUrl::fromLocalFile(launchLog)))
            status->setText(tr("Log file: %1").arg(launchLog));
    });
    connect(paused, &QCheckBox::toggled, this, [](bool value) {
        QSettings().setValue("simulator/startPaused", value);
    });

    connect(&simulator, &QProcess::started, this, &QWidget::hide);
    connect(&simulator, &QProcess::errorOccurred, this, [this](QProcess::ProcessError error) {
        if (error == QProcess::FailedToStart) {
            showWindow();
            status->setText(tr("Orbiter could not start: %1").arg(simulator.errorString()));
        }
    });
    connect(&simulator, &QProcess::finished, this, [this](int code, QProcess::ExitStatus exitStatus) {
        const auto *item = scenarios->currentItem();
        const auto path = item ? item->data(0, ScenarioRole).toString() : QString();
        refreshScenarios(path);
        showWindow();
        status->setText(exitStatus == QProcess::CrashExit ? tr("Orbiter closed unexpectedly.")
                        : code != 0 ? tr("Orbiter exited with code %1.").arg(code)
                                    : tr("Session ended."));
        openLog->setVisible(QFileInfo(launchLog).isFile());
    });

    QSettings settings;
    paused->setChecked(settings.value("simulator/startPaused", true).toBool());
    const auto remembered = settings.value("simulator/profile").toString();
    if (!profilePath.isEmpty())
        loadProfile(profilePath);
    else if (!remembered.isEmpty())
        loadProfile(remembered);
#ifdef Q_OS_WIN
    else {
        const auto exe = settings.value("simulator/windowsExecutable").toString();
        const auto adjacent = QDir(QCoreApplication::applicationDirPath()).filePath("Orbiter.exe");
        useProfile(exe.isEmpty() && !QFileInfo(adjacent).isFile()
                       ? SimulatorProfile{} : SimulatorProfile::fromWindowsExecutable(exe.isEmpty() ? adjacent : exe));
    }
#else
    else
        useProfile({});
#endif
}

void Launchpad::loadProfile(const QString &path)
{
    try {
        auto selected = SimulatorProfile::load(path);
        useProfile(selected);
        QSettings().setValue("simulator/profile", QFileInfo(path).absoluteFilePath());
    } catch (const std::exception &error) {
        status->setText(tr("Could not read the simulator profile: %1").arg(QString::fromUtf8(error.what())));
    }
}

void Launchpad::useProfile(SimulatorProfile selected)
{
    profile = std::move(selected);
    launchLog.clear();
    openLog->hide();
    paused->setVisible(profile.native);
    search->clear();
    refreshScenarios(QSettings().value("simulator/lastScenario").toString());
    const auto error = profile.validationError();
    status->setText(error.isEmpty() ? QFileInfo(profile.executable).fileName() : error);
}

void Launchpad::refreshScenarios(const QString &selectedPath)
{
    scenarios->clear();
    addScenarios(profile.scenarioRoot);
    if (profile.native && QFileInfo(profile.saveRoot).isDir() && profile.scenarioRoot != profile.saveRoot) {
        auto *savedFolder = new QTreeWidgetItem(scenarios, {tr("Saved scenarios")});
        savedFolder->setIcon(0, style()->standardIcon(QStyle::SP_DirIcon));
        addScenarios(profile.saveRoot, savedFolder);
        if (savedFolder->childCount() == 0)
            delete savedFolder;
    }
    scenarios->sortItems(0, Qt::AscendingOrder);
    filterScenarios();
    QTreeWidgetItem *candidate = nullptr;
    for (QTreeWidgetItemIterator it(scenarios, QTreeWidgetItemIterator::NotHidden); *it; ++it) {
        const auto path = (*it)->data(0, ScenarioRole).toString();
        if (path.isEmpty())
            continue;
        if (!candidate || path == selectedPath)
            candidate = *it;
        if (path == selectedPath)
            break;
    }
    if (candidate) {
        for (auto *parent = candidate->parent(); parent; parent = parent->parent())
            parent->setExpanded(true);
        scenarios->setCurrentItem(candidate);
        scenarios->scrollToItem(candidate);
    }
    showSelection();
}

void Launchpad::addScenarios(const QString &root, QTreeWidgetItem *savedFolder)
{
    if (root.isEmpty() || !QFileInfo(root).isDir())
        return;
    const QDir base(root);
    QMap<QString, QTreeWidgetItem *> folders;
    QDirIterator files(root, QDir::Files | QDir::Readable | QDir::NoSymLinks, QDirIterator::Subdirectories);
    const auto folderIcon = style()->standardIcon(QStyle::SP_DirIcon);
    const auto fileIcon = style()->standardIcon(QStyle::SP_FileIcon);
    while (files.hasNext()) {
        const QFileInfo file(files.next());
        if (file.suffix().compare("scn", Qt::CaseInsensitive) != 0)
            continue;
        const auto parts = base.relativeFilePath(file.absoluteFilePath()).split('/');
        QString relativeFolder;
        auto *parent = savedFolder ? savedFolder : scenarios->invisibleRootItem();
        for (qsizetype i = 0; i + 1 < parts.size(); ++i) {
            relativeFolder = relativeFolder.isEmpty() ? parts[i] : relativeFolder + '/' + parts[i];
            auto *&folder = folders[relativeFolder];
            if (!folder) {
                folder = new QTreeWidgetItem(parent, {parts[i]});
                folder->setIcon(0, folderIcon);
                folder->setData(0, DescriptionRole, base.filePath(relativeFolder + "/Description.txt"));
            }
            parent = folder;
        }
        auto *item = new QTreeWidgetItem(parent, {file.completeBaseName()});
        item->setIcon(0, fileIcon);
        item->setData(0, ScenarioRole, file.absoluteFilePath());
        item->setData(0, DescriptionRole, file.absoluteFilePath());
    }
}

void Launchpad::filterScenarios()
{
    const auto query = search->text().trimmed();
    for (int i = 0; i < scenarios->topLevelItemCount(); ++i)
        filterItem(scenarios->topLevelItem(i), query, false);
    if (auto *item = scenarios->currentItem(); item && item->isHidden())
        scenarios->setCurrentItem(nullptr);
    showSelection();
}

void Launchpad::showSelection()
{
    const auto *item = scenarios->currentItem();
    const auto path = item ? item->data(0, ScenarioRole).toString() : QString();
    title->setText(item ? item->text(0) : tr("Select a scenario"));
    location->setText(path.isEmpty() ? QString() : QFileInfo(path).dir().dirName());
    location->setVisible(!path.isEmpty());
    const auto text = item ? readDescription(item->data(0, DescriptionRole).toString(), profile.helpRoot, path.isEmpty())
                           : QString();
    if (!text.isEmpty())
        description->setHtml(text);
    else
        description->setPlainText(path.isEmpty() ? QString() : tr("No description available."));
    launch->setEnabled(!path.isEmpty() && profile.validationError().isEmpty()
                       && simulator.state() == QProcess::NotRunning);
}

void Launchpad::launchScenario()
{
    const auto *item = scenarios->currentItem();
    if (!item || simulator.state() != QProcess::NotRunning)
        return;
    const auto path = item->data(0, ScenarioRole).toString();
    if (!QFileInfo(path).isFile()) {
        status->setText(tr("The selected scenario is missing. Refresh the scenario list."));
        return;
    }
    const auto error = profile.validationError();
    if (!error.isEmpty()) {
        status->setText(error);
        return;
    }
    if (profile.native && !QDir().mkpath(profile.saveRoot)) {
        status->setText(tr("Could not create the saves folder: %1").arg(profile.saveRoot));
        return;
    }
    launchLog = QDir(profile.workingDirectory).filePath(profile.native ? "orbiter-session.log" : "Orbiter.log");
    openLog->hide();
    simulator.setWorkingDirectory(profile.workingDirectory);
    simulator.setProcessEnvironment(profile.environment);
    simulator.setProcessChannelMode(QProcess::MergedChannels);
    simulator.setStandardOutputFile(profile.native ? launchLog : QProcess::nullDevice());
    QSettings().setValue("simulator/lastScenario", path);
    status->setText(tr("Starting %1…").arg(item->text(0)));
    launch->setEnabled(false);
    simulator.start(profile.executable, profile.arguments(path, paused->isChecked()));
}

void Launchpad::showWindow()
{
    show();
    raise();
    activateWindow();
    showSelection();
}

void Launchpad::closeEvent(QCloseEvent *event)
{
    if (simulator.state() == QProcess::NotRunning)
        QWidget::closeEvent(event);
    else
        event->ignore();
}
