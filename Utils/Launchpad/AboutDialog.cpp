// Licensed under the MIT License
#include "AboutDialog.h"
#include "SimulatorProfile.h"
#include "about.hpp"

#include <QDate>
#include <QDialog>
#include <QDialogButtonBox>
#include <QFile>
#include <QFileInfo>
#include <QFormLayout>
#include <QHBoxLayout>
#include <QLabel>
#include <QLocale>
#include <QPixmap>
#include <QTabWidget>
#include <QTextBrowser>
#include <QVBoxLayout>

namespace {
QString simulatorBuild(const SimulatorProfile &profile)
{
    if (profile.executable.isEmpty())
        return QObject::tr("Choose a simulator profile to see its build.");
    const QString path = QFileInfo(profile.executable).canonicalFilePath();
    QFile stamp(path + ".version");
    if (!path.isEmpty() && stamp.open(QIODevice::ReadOnly) && stamp.size() <= 32) {
        const QString version = QString::fromLatin1(stamp.readAll().trimmed());
        const QDate date = QDate::fromString("20" + version, "yyyyMMdd");
        if (version.size() == 6 && date.isValid())
            return QObject::tr("Build %1 [v.%2]").arg(QLocale::c().toString(date, "dd MMM yyyy"), version);
    }
    return QObject::tr("Version unavailable for %1").arg(QFileInfo(profile.executable).fileName());
}

QLabel *plainLabel(const QString &text)
{
    auto *label = new QLabel;
    label->setTextFormat(Qt::PlainText);
    label->setText(text);
    label->setTextInteractionFlags(Qt::TextSelectableByMouse);
    label->setWordWrap(true);
    return label;
}

QLabel *webLink(const QString &address)
{
    auto *label = new QLabel;
    label->setTextFormat(Qt::RichText);
    label->setTextInteractionFlags(Qt::TextBrowserInteraction);
    label->setOpenExternalLinks(true);
    label->setText(QStringLiteral("<a style='color:#8fd5f6' href='https://%1'>%1</a>").arg(address));
    return label;
}
}

void showAboutDialog(QWidget *parent, const SimulatorProfile &profile)
{
    QDialog dialog(parent);
    dialog.setObjectName("orbiterAbout");
    dialog.setWindowTitle(QObject::tr("About Orbiter"));
    dialog.resize(640, 490);
    auto *layout = new QVBoxLayout(&dialog);
    auto *tabs = new QTabWidget;
    layout->addWidget(tabs);

    auto *overview = new QWidget;
    auto *info = new QVBoxLayout(overview);
    info->setContentsMargins(16, 16, 16, 12);
    auto *heading = new QHBoxLayout;
    auto *icon = new QLabel;
    icon->setPixmap(QPixmap(":/launchpad/Icon64.bmp"));
    heading->addWidget(icon);
    auto *identity = new QVBoxLayout;
    auto *name = plainLabel(QStringLiteral(NAME1));
    QFont font = name->font();
    font.setBold(true);
    name->setFont(font);
    identity->addWidget(name);
    identity->addWidget(plainLabel(QStringLiteral(SIG1B)));
    heading->addLayout(identity, 1);
    info->addLayout(heading);
    auto *builds = new QFormLayout;
    auto *sim = plainLabel(simulatorBuild(profile));
    sim->setObjectName("aboutSimulatorBuild");
    builds->addRow(QObject::tr("Selected simulator"), sim);
    auto *launcher = plainLabel(QStringLiteral(SIG4));
    launcher->setObjectName("aboutLaunchpadBuild");
    builds->addRow(QObject::tr("Qt Launchpad"), launcher);
    info->addLayout(builds);
    info->addSpacing(6);
    info->addWidget(plainLabel(QObject::tr("Component credits")));
    info->addWidget(plainLabel(QStringLiteral(CREDIT_D3D9)));
    info->addWidget(plainLabel(QStringLiteral(CREDIT_XRSOUND)));
    info->addSpacing(6);
    auto *links = new QFormLayout;
    links->addRow(QObject::tr("Orbiter home"), webLink(QStringLiteral(SIG2)));
    links->addRow(QObject::tr("Orbiter forum"), webLink(QStringLiteral(SIG5)));
    links->addRow(QObject::tr("YouTube channel"), webLink(QStringLiteral(SIG6)));
    info->addLayout(links);
    info->addStretch();
    tabs->addTab(overview, QObject::tr("About Orbiter"));

    auto *credits = new QTextBrowser;
    credits->setObjectName("aboutCredits");
    credits->setOpenExternalLinks(true);
    credits->setSource(QUrl("qrc:/launchpad/about/Html/Main/Credit/credit.htm"));
    tabs->addTab(credits, QObject::tr("Credits and Contributions"));

    auto *license = new QTextBrowser;
    license->setObjectName("aboutLicense");
    QFile terms(":/launchpad/about/Src/Orbiter/Disclaimer.txt");
    if (terms.open(QIODevice::ReadOnly))
        license->setPlainText(QString::fromUtf8(terms.readAll()));
    tabs->addTab(license, QObject::tr("MIT License"));

    auto *buttons = new QDialogButtonBox(QDialogButtonBox::Close);
    QObject::connect(buttons, &QDialogButtonBox::rejected, &dialog, &QDialog::reject);
    layout->addWidget(buttons);
    dialog.exec();
}
