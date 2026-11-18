#pragma once

#include <QMap>
#include <QWidget>
#include <array>
#include <functional>

class QComboBox;
class QDoubleSpinBox;
class QFormLayout;
class QSpinBox;
struct SimulatorProfile;

class ExtraPage : public QWidget {
public:
    using Lookup = std::function<QString(const QString &)>;
    ExtraPage(const SimulatorProfile &profile, const Lookup &read);
    QMap<QString, QString> values() const;
    QString propagationError() const;
private:
    struct Stage {
        QComboBox *method;
        // Time and angle targets followed by the two stage transition limits.
        std::array<QDoubleSpinBox *, 4> fields;
        std::array<double, 4> displayed;
        std::array<QString, 4> stored;
    };
    QSpinBox *count;
    std::array<Stage, 5> stages;
    QMap<QString, std::function<QString()>> bindings;
};
