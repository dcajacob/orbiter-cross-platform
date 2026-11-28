#pragma once

#include <QLabel>
#include <QPixmap>
#include <QSplitter>
#include <QVBoxLayout>

// The scenario browser and the runtime chooser share the same window frame.
struct LaunchpadFrame {
    QHBoxLayout *header;
    QVBoxLayout *left;
    QVBoxLayout *right;
    QHBoxLayout *footer;

    explicit LaunchpadFrame(QWidget *window)
    {
        window->setObjectName("launchpad");
        window->setAttribute(Qt::WA_StyledBackground);
        window->resize(1000, 680);
        window->setMinimumSize(690, 440);
        auto *outer = new QVBoxLayout(window);
        outer->setContentsMargins(24, 22, 24, 18);
        outer->setSpacing(16);
        header = new QHBoxLayout;
        auto *heading = new QLabel(QWidget::tr("Orbiter Launchpad"));
        heading->setObjectName("heading");
        heading->setAccessibleName(QWidget::tr("Orbiter Space Flight Simulator"));
        const QPixmap banner(":/launchpad/banner.bmp");
        if (!banner.isNull())
            heading->setPixmap(banner);
        header->addWidget(heading);
        header->addStretch();
        outer->addLayout(header);

        auto *splitter = new QSplitter;
        splitter->setChildrenCollapsible(false);
        auto *listPane = new QWidget;
        left = new QVBoxLayout(listPane);
        left->setContentsMargins(0, 0, 8, 0);
        left->setSpacing(8);
        splitter->addWidget(listPane);
        auto *detailPane = new QWidget;
        right = new QVBoxLayout(detailPane);
        right->setContentsMargins(8, 0, 0, 0);
        right->setSpacing(8);
        splitter->addWidget(detailPane);
        splitter->setSizes({330, 600});
        splitter->setStretchFactor(1, 1);
        outer->addWidget(splitter, 1);
        footer = new QHBoxLayout;
        outer->addLayout(footer);
    }
};
