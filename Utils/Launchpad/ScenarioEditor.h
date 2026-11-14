#pragma once

#include <QString>

class QWidget;

// Returns the new scenario path, or an empty string if the dialog is cancelled.
QString copyStockScenario(QWidget *parent, const QString &source, const QString &stockRoot,
                          const QString &saveRoot);
