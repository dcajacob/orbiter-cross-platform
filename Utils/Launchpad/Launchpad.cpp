#include "Launchpad.h"
#include "AboutDialog.h"
#include "FlightSettings.h"
#include "ScenarioEditor.h"
#ifdef ORBITER_LAUNCHPAD_JOYSTICK
#include "JoystickSetup.h"
#endif

#include <QCheckBox>
#include <QCloseEvent>
#include <QDesktopServices>
#include <QDirIterator>
#include <QFile>
#include <QFileDialog>
#include <QFileInfo>
#include <QHBoxLayout>
#include <QImageReader>
#include <QLabel>
#include <QLineEdit>
#include <QMap>
#include <QMenu>
#include <QPixmap>
#include <QPushButton>
#include <QScrollBar>
#include <QSettings>
#include <QShortcut>
#include <QSplitter>
#include <QStyle>
#include <QTextBrowser>
#include <QTextBlock>
#include <QTextCursor>
#include <QTextImageFormat>
#include <QTreeWidget>
#include <QTreeWidgetItemIterator>
#include <QUrl>
#include <QVBoxLayout>

#include <algorithm>
#include <exception>

namespace {
const QString bundledHelp = QStringLiteral(":/launchpad/scenarios");

struct ScenarioDescription {
    QString html;
    QUrl base;
    QString imageRoot;
};

QString fileUnder(const QString &root, const QString &path)
{
    if (root.isEmpty())
        return {};
    const QFileInfo file(path);
    const auto canonical = file.canonicalFilePath();
    return canonical.startsWith(root + '/') && file.isFile() ? canonical : QString();
}
}

class ScenarioBrowser final : public QTextBrowser {
public:
    void showDescription(const ScenarioDescription &content, const QString &fallback)
    {
        imageRoot = content.imageRoot;
        document()->setBaseUrl(content.base);
        if (content.html.isEmpty())
            setPlainText(fallback);
        else
            setHtml(content.html);
        fitImages();
        verticalScrollBar()->setValue(0);
        horizontalScrollBar()->setValue(0);
    }

protected:
    QVariant loadResource(int type, const QUrl &name) override
    {
        if (type != QTextDocument::ImageResource)
            return {};
        const auto url = document()->baseUrl().resolved(name);
        QString path;
        if (imageRoot == bundledHelp && url.scheme() == "qrc" && url.authority().isEmpty()) {
            const auto resource = QDir::cleanPath(':' + url.path());
            if (resource.startsWith(bundledHelp + '/'))
                path = resource;
        } else if (!imageRoot.isEmpty() && url.isLocalFile() && url.host().isEmpty()) {
            path = fileUnder(imageRoot, url.toLocalFile());
        }
        if (!path.isEmpty()) {
            QImageReader reader(path);
            const auto format = reader.format();
            const auto size = reader.size();
            if ((format == "jpeg" || format == "png" || format == "gif")
                && size.isValid() && size.width() <= 4096 && size.height() <= 4096) {
                const auto image = reader.read();
                if (!image.isNull())
                    return image;
            }
        }
        // A valid transparent image also prevents Qt's fallback image loader
        // from opening a URL that this browser declined.
        QImage transparent(1, 1, QImage::Format_ARGB32_Premultiplied);
        transparent.fill(Qt::transparent);
        return transparent;
    }

    void resizeEvent(QResizeEvent *event) override
    {
        QTextBrowser::resizeEvent(event);
        fitImages();
    }

private:
    void fitImages()
    {
        const auto available = viewport()->width() - 2 * document()->documentMargin();
        if (available <= 0)
            return;
        QList<QPair<int, QTextImageFormat>> changes;
        for (auto block = document()->begin(); block.isValid(); block = block.next()) {
            for (auto it = block.begin(); !it.atEnd(); ++it) {
                const auto fragment = it.fragment();
                if (!fragment.charFormat().isImageFormat())
                    continue;
                auto image = fragment.charFormat().toImageFormat();
                const auto resource = document()->resource(QTextDocument::ImageResource, QUrl(image.name())).value<QImage>();
                if (resource.isNull())
                    continue;
                const auto preferred = image.doubleProperty(QTextFormat::UserProperty);
                const auto naturalWidth = preferred > 0 ? preferred : resource.width();
                const auto width = std::min<qreal>(naturalWidth, available);
                const auto height = width * resource.height() / resource.width();
                if (image.width() == width && image.height() == height)
                    continue;
                image.setProperty(QTextFormat::UserProperty, naturalWidth);
                image.setWidth(width);
                image.setHeight(height);
                changes.append({fragment.position(), image});
            }
        }
        for (const auto &[position, format] : changes) {
            QTextCursor cursor(document());
            cursor.setPosition(position);
            cursor.movePosition(QTextCursor::NextCharacter, QTextCursor::KeepAnchor);
            cursor.setCharFormat(format);
        }
    }

    QString imageRoot;
};

namespace {
constexpr int DescriptionRole = Qt::UserRole;
constexpr int ScenarioRole = Qt::UserRole + 1;
constexpr int StockRole = Qt::UserRole + 2;

ScenarioDescription helpDescription(const QString &relative, const QString &helpRoot)
{
    const auto root = QFileInfo(helpRoot).canonicalFilePath();
    const auto local = fileUnder(root, QDir(root).filePath(relative));
    QFile page(local);
    if (!local.isEmpty() && page.open(QIODevice::ReadOnly))
        return {QString::fromUtf8(page.read(256 * 1024)), QUrl::fromLocalFile(local), root};

    const auto resource = QDir::cleanPath(bundledHelp + '/' + relative);
    if (!resource.startsWith(bundledHelp + '/'))
        return {};
    page.setFileName(resource);
    if (page.open(QIODevice::ReadOnly))
        return {QString::fromUtf8(page.read(256 * 1024)), QUrl("qrc" + resource), bundledHelp};
    return {};
}

ScenarioDescription readDescription(const QString &path, const QString &helpRoot, bool folder)
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
                return {content, QUrl::fromLocalFile(QFileInfo(path).absoluteFilePath()), {}};
            if (kind == "DESC")
                return {"<p>" + content.toHtmlEscaped().replace('\n', "<br>") + "</p>", {}, {}};

            const auto parts = content.split(',');
            if (parts.size() != 2)
                break;
            const auto book = parts[0].trimmed().replace('\\', '/');
            return helpDescription(book + '/' + parts[1].trimmed() + ".htm", helpRoot);
        } else {
            body.append(line);
        }
    }
    if (kind.isEmpty() && folder)
        return {"<p>" + source.toHtmlEscaped().replace('\n', "<br>") + "</p>", {}, {}};
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
    heading->setAccessibleName(tr("Orbiter Space Flight Simulator"));
    const QPixmap banner(":/launchpad/banner.bmp");
    if (!banner.isNull())
        heading->setPixmap(banner);
    header->addWidget(heading);
    header->addStretch();
    flightSettings = new QPushButton(tr("Flight settings…"));
    flightSettings->setObjectName("flightSettingsButton");
    connect(flightSettings, &QPushButton::clicked, this, [this] {
        const auto selected = selectedProfile();
        showFlightSettings(this, selected);
        showSelection();
        const auto error = selected.validationError();
        status->setText(error.isEmpty() ? QFileInfo(profile.executable).fileName() : error);
    });
    header->addWidget(flightSettings);
    auto *setup = new QPushButton(tr("Setup"));
    auto *setupMenu = new QMenu(setup);
    setupMenu->addAction(tr("Open simulator profile…"), this, [this] {
        const auto path = QFileDialog::getOpenFileName(this, tr("Open simulator profile"), {}, tr("JSON profiles (*.json)"));
        if (!path.isEmpty())
            loadProfile(path);
    });
#ifdef ORBITER_LAUNCHPAD_JOYSTICK
    auto *joystick = setupMenu->addAction(tr("Joystick setup…"), this, &Launchpad::openJoystickSetup);
    connect(setupMenu, &QMenu::aboutToShow, this, [this, joystick] {
        joystick->setEnabled(profile.native && QFileInfo(selectedProfile().config).isFile()
                             && simulator.state() == QProcess::NotRunning);
    });
#endif
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
    auto *about = new QPushButton(tr("About"));
    about->setObjectName("aboutButton");
    connect(about, &QPushButton::clicked, this, &Launchpad::openAbout);
    header->addWidget(about);
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
    copy = new QPushButton(tr("Copy and edit…"));
    copy->setObjectName("copyScenarioButton");
    copy->setEnabled(false);
    footer->addWidget(status, 1);
    footer->addWidget(openLog);
    footer->addWidget(paused);
    footer->addSpacing(6);
    footer->addWidget(copy);
    footer->addWidget(launch);
    outer->addLayout(footer);

    connect(search, &QLineEdit::textChanged, this, &Launchpad::filterScenarios);
    auto *find = new QShortcut(QKeySequence::Find, this);
    connect(find, &QShortcut::activated, search, [this] {
        search->setFocus();
        search->selectAll();
    });
    // An accessibility client can select a row without moving the keyboard cursor.
    // The preview and launch action should follow that selection as they do a mouse click.
    connect(scenarios, &QTreeWidget::itemSelectionChanged, this, [this] {
        const auto selected = scenarios->selectedItems();
        if (!selected.isEmpty() && selected.front() != scenarios->currentItem())
            scenarios->setCurrentItem(selected.front());
    });
    connect(scenarios, &QTreeWidget::currentItemChanged, this, &Launchpad::showSelection);
    connect(scenarios, &QTreeWidget::itemActivated, this, [this](QTreeWidgetItem *item, int) {
        if (item && !item->data(0, ScenarioRole).toString().isEmpty())
            launchScenario();
    });
    connect(launch, &QPushButton::clicked, this, &Launchpad::launchScenario);
    connect(copy, &QPushButton::clicked, this, &Launchpad::copyScenario);
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

void Launchpad::openAbout()
{
    showAboutDialog(this, profile);
}

void Launchpad::openJoystickSetup()
{
#ifdef ORBITER_LAUNCHPAD_JOYSTICK
    const auto selected = selectedProfile();
    if (selected.native && QFileInfo(selected.config).isFile() && simulator.state() == QProcess::NotRunning)
        showJoystickSetup(this, selected.config, selected.keymap);
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
    copy->setVisible(profile.native);
    search->clear();
    refreshScenarios(QSettings().value("simulator/lastScenario").toString());
    const auto error = selectedProfile().validationError();
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
        item->setData(0, StockRole, !savedFolder);
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

SimulatorProfile Launchpad::selectedProfile() const
{
    const auto *item = scenarios->currentItem();
    return item ? profile.forScenario(item->data(0, ScenarioRole).toString()) : profile;
}

void Launchpad::showSelection()
{
    const auto *item = scenarios->currentItem();
    const auto path = item ? item->data(0, ScenarioRole).toString() : QString();
    title->setText(item ? item->text(0) : tr("Select a scenario"));
    location->setText(path.isEmpty() ? QString() : QFileInfo(path).dir().dirName());
    location->setVisible(!path.isEmpty());
    const auto content = item ? readDescription(item->data(0, DescriptionRole).toString(), profile.helpRoot, path.isEmpty())
                              : ScenarioDescription();
    description->showDescription(content, path.isEmpty() ? QString() : tr("No description available."));
    const auto selected = selectedProfile();
    flightSettings->setEnabled(selected.configured && QFileInfo(selected.config).isFile());
    flightSettings->setToolTip(selected.config != profile.config
        ? tr("Edit flight settings for %1").arg(item->text(0)) : QString());
    launch->setEnabled(!path.isEmpty() && selected.validationError().isEmpty()
                       && simulator.state() == QProcess::NotRunning);
    copy->setEnabled(profile.native && item && item->data(0, StockRole).toBool()
                     && simulator.state() == QProcess::NotRunning);
}

void Launchpad::copyScenario()
{
    const auto *item = scenarios->currentItem();
    if (!copy->isEnabled() || !item)
        return;
    try {
        const auto path = copyStockScenario(this, item->data(0, ScenarioRole).toString(),
                                            profile.scenarioRoot, profile.saveRoot);
        if (path.isEmpty())
            return;
        search->clear();
        refreshScenarios(path);
        status->setText(tr("Created %1.").arg(QFileInfo(path).fileName()));
    } catch (const std::exception &error) {
        status->setText(QString::fromUtf8(error.what()));
    }
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
    const auto selected = selectedProfile();
    const auto error = selected.validationError();
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
    simulator.start(selected.executable, selected.arguments(path, paused->isChecked()));
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
