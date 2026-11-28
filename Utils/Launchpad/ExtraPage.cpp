#include "ExtraPage.h"
#include "SimulatorProfile.h"
#include "../../Src/Orbiter/PhysicsConfig.h"

#include <QCheckBox>
#include <QComboBox>
#include <QDir>
#include <QDoubleSpinBox>
#include <QFormLayout>
#include <QRegularExpression>
#include <QSpinBox>
#include <QStackedWidget>
#include <QVBoxLayout>
#include <QtMath>
#include <cmath>
#include <limits>

namespace {
constexpr double radians = qDegreesToRadians(1.0);
const std::array<double, 4> units = {1, radians, 1, radians};
// The stock stage tables in Config.cpp use seconds and radians.
constexpr double defaults[5][4] = {
    {0.1, 0.2*radians, 0.5, radians}, {2, 2*radians, 10, 4*radians},
    {20, 5*radians, 100, 10*radians}, {200, 20*radians, 1e10, 1e10},
    {500, 50*radians, 1e10, 1e10}
};
constexpr int methods[] = {PROP_RK4, PROP_RK4, PROP_RK6, PROP_RK8, PROP_RK8};

QDoubleSpinBox *number(QFormLayout *form, const QString &key, const QString &label,
                       double value, double minimum, double maximum, const QString &suffix)
{
    auto *field = new QDoubleSpinBox;
    field->setObjectName(key);
    field->setDecimals(8);
    field->setRange(minimum, maximum);
    field->setValue(value);
    field->setSuffix(suffix);
    field->setStepType(QAbstractSpinBox::AdaptiveDecimalStepType);
    form->addRow(label, field);
    return field;
}

QString decimal(double value) { return QString::number(value, 'g', 16); }

int integer(const QString &text, int fallback)
{
    bool ok;
    const int value = text.toInt(&ok);
    return ok ? value : fallback;
}
}

ExtraPage::ExtraPage(const SimulatorProfile &profile, const Lookup &read)
{
    auto *layout = new QVBoxLayout(this);
    auto *section = new QComboBox;
    section->setObjectName("extraSection");
    auto *pages = new QStackedWidget;
    layout->addWidget(section);
    layout->addWidget(pages);
    layout->addStretch();
    connect(section, &QComboBox::currentIndexChanged, pages, &QStackedWidget::setCurrentIndex);
    auto page = [&](const QString &name) {
        auto *widget = new QWidget;
        auto *form = new QFormLayout(widget);
        pages->addWidget(widget);
        section->addItem(name);
        return form;
    };
    auto whole = [&](QFormLayout *form, const QString &key, const QString &label,
                     int fallback, int minimum, int maximum) {
        auto *box = new QSpinBox;
        box->setObjectName(key);
        box->setRange(minimum, maximum);
        box->setValue(integer(read(key), fallback));
        form->addRow(label, box);
        bindings.insert(key, [box] { return QString::number(box->value()); });
        return box;
    };
    using Choices = QList<QPair<QString, QString>>;
    auto choice = [&](QFormLayout *form, const QString &key, const QString &label, const Choices &items) {
        auto *box = new QComboBox;
        box->setObjectName(key);
        for (const auto &item : items) box->addItem(item.first, item.second);
        const auto value = read(key);
        const int index = box->findData(value, Qt::UserRole, Qt::MatchFixedString);
        box->setCurrentIndex(qMax(0, index));
        form->addRow(label, box);
        bindings.insert(key, [box] { return box->currentData().toString(); });
        return box;
    };

    auto *dynamics = page(tr("Dynamic state propagators"));
    count = whole(dynamics, "PropStages", tr("Active stages"), 4, 1, 5);
    whole(dynamics, "PropSubsampling", tr("Maximum substeps"), 10, 1, std::numeric_limits<int>::max());
    auto *stageChoice = new QComboBox;
    stageChoice->setObjectName("extraStage");
    dynamics->addRow(tr("Edit stage"), stageChoice);
    auto *stagePages = new QStackedWidget;
    dynamics->addRow(stagePages);
    connect(stageChoice, &QComboBox::currentIndexChanged, stagePages, &QStackedWidget::setCurrentIndex);
    const QStringList labels = {tr("Target time step"), tr("Target angular step"),
                                tr("Time limit for this stage"), tr("Angle limit for this stage")};
    for (int i = 0; i < int(stages.size()); ++i) {
        const auto key = QString("PropStage%1").arg(i);
        const auto tokens = read(key).simplified().split(' ', Qt::SkipEmptyParts);
        auto &stage = stages[i];
        auto *widget = new QWidget;
        auto *form = new QFormLayout(widget);
        stagePages->addWidget(widget);
        stage.method = new QComboBox;
        stage.method->setObjectName(key + "Method");
        stage.method->addItems({"RK2", "RK4", "RK5", "RK6", "RK7", "RK8", "SY2", "SY4", "SY6", "SY8"});
        stage.method->setToolTip(tr("RK uses Runge–Kutta integration. SY uses symplectic integration."));
        const int method = integer(tokens.value(0), methods[i]);
        stage.method->setCurrentIndex(method >= 0 && method < 10 ? method : methods[i]);
        form->addRow(tr("Integration method"), stage.method);
        for (int j = 0; j < 4; ++j) {
            bool ok;
            const auto token = tokens.value(j + 1);
            const double raw = token.toDouble(&ok);
            const bool valid = ok && std::isfinite(raw) && raw > 0;
            const double value = valid ? raw : defaults[i][j];
            stage.stored[j] = valid ? token : decimal(value);
            stage.fields[j] = number(form, key + QString("Field%1").arg(j), labels[j],
                                     value / units[j], 1e-8, 1e12, j%2 ? tr(" °") : tr(" s"));
            stage.displayed[j] = stage.fields[j]->value();
        }
    }
    auto updateStages = [this, stageChoice](int n) {
        while (stageChoice->count() < n) stageChoice->addItem(QString::number(stageChoice->count() + 1));
        while (stageChoice->count() > n) stageChoice->removeItem(stageChoice->count() - 1);
        for (int i = 0; i < n; ++i) {
            auto &stage = stages[i];
            auto *form = qobject_cast<QFormLayout *>(stage.method->parentWidget()->layout());
            for (int j : {2, 3}) form->setRowVisible(stage.fields[j], i + 1 < n);
        }
    };
    updateStages(count->value());
    connect(count, &QSpinBox::valueChanged, this, updateStages);

    auto *orbit = page(tr("Orbit stabilisation"));
    auto *stabilise = new QCheckBox(tr("Enable orbit stabilisation"));
    stabilise->setObjectName("StabiliseOrbits");
    stabilise->setChecked(!read("StabiliseOrbits").startsWith("FALSE", Qt::CaseInsensitive));
    orbit->addRow(stabilise);
    bindings.insert("StabiliseOrbits", [stabilise] { return stabilise->isChecked() ? "TRUE" : "FALSE"; });
    auto percent = [&](const QString &key, const QString &label, double fallback, double high) {
        bool ok;
        const double fraction = read(key).toDouble(&ok);
        auto *box = number(orbit, key, label, ok ? fraction*100 : fallback, 0, high, tr(" %"));
        box->setEnabled(stabilise->isChecked());
        connect(stabilise, &QCheckBox::toggled, box, &QWidget::setEnabled);
        bindings.insert(key, [box] { return decimal(box->value()/100); });
    };
    percent("StabilisePLimit", tr("Maximum perturbing gravity"), 5, 100);
    percent("StabiliseSLimit", tr("Minimum step as share of orbit"), 1, 1e10);

    auto *instruments = page(tr("Cockpit displays (MFDs)"));
    auto *pow2 = choice(instruments, "ForceMfdPow2", tr("2D display texture size"),
                        {{tr("Automatic"), "AUTO"}, {tr("Match display"), "FALSE"},
                         {tr("Use 256 or 512 pixels"), "TRUE"}});
    auto *threshold = whole(instruments, "MfdHiresThreshold", tr("Switch to 512 pixels at"),
                            384, 8, std::numeric_limits<int>::max());
    threshold->setSuffix(tr(" px"));
    auto enableThreshold = [pow2, threshold] { threshold->setEnabled(pow2->currentData() == "TRUE"); };
    connect(pow2, &QComboBox::currentIndexChanged, this, enableThreshold);
    enableThreshold();
    choice(instruments, "VCMfdSize", tr("Virtual cockpit display size"),
           {{"512 × 512", "512"}, {"256 × 256", "256"}, {"1024 × 1024", "1024"}});

    if (profile.assets.isEmpty() || profile.modules.isEmpty()) return;
    QDir assets(profile.assets);
    QDir bodies(QDir(profile.modules).filePath("Celbody"));
    QFormLayout *atmospheres = nullptr;
    const QRegularExpression moduleName("^[A-Za-z0-9_-]+$");
    for (const auto &body : bodies.entryList(QDir::Dirs | QDir::NoDotAndDotDot)) {
        if (!moduleName.match(body).hasMatch()) continue;
        QDir models(bodies.filePath(body + "/Atmosphere"));
        Choices items{{tr("Installation default"), "DEFAULT"}, {tr("No atmosphere module"), "[None]"}};
        for (const auto &file : models.entryInfoList({"*.so"}, QDir::Files, QDir::Name)) {
            const auto model = file.completeBaseName();
            if (moduleName.match(model).hasMatch()) items.append({model, model});
        }
        const auto key = "NativeAtmosphere_" + body;
        const auto selected = read(key);
        if (items.size() == 2 && selected.isEmpty()) continue;
        if (!atmospheres) atmospheres = page(tr("Planet atmospheres"));
        auto *box = choice(atmospheres, key, body, items);
        if (!selected.isEmpty() && box->findData(selected) < 0) {
            box->addItem(tr("Unavailable (%1)").arg(selected), selected);
            box->setCurrentIndex(box->count() - 1);
        }
    }
    QFormLayout *vessels = nullptr;
    auto resolution = [&](const QString &key, const QString &label) {
        if (!vessels) vessels = page(tr("Vessel graphics"));
        choice(vessels, key, label, {{tr("Installation default"), "DEFAULT"},
                                     {tr("Standard resolution"), "FALSE"}, {tr("High resolution"), "TRUE"}});
    };
    for (const QString &vessel : {QString("DG"), QString("Atlantis")}) {
        if (assets.exists("Textures2/" + vessel) || assets.exists("Textures2/~" + vessel))
            resolution("Native" + vessel + "HighResTextures",
                       vessel == "DG" ? tr("Delta-glider textures") : tr("Atlantis textures"));
    }
    if (assets.exists("Meshes/Atlantis/AtlantisVC.msh") &&
        (assets.exists("Meshes/Atlantis/~AtlantisVC_lo.msh") || assets.exists("Meshes/Atlantis/~AtlantisVC_hi.msh")))
        resolution("NativeAtlantisHighResCockpit", tr("Atlantis cockpit mesh"));
}

QMap<QString, QString> ExtraPage::values() const
{
    QMap<QString, QString> result;
    for (auto it = bindings.cbegin(); it != bindings.cend(); ++it) result.insert(it.key(), it.value()());
    for (int i = 0; i < int(stages.size()); ++i) {
        const auto &stage = stages[i];
        QStringList tokens{QString::number(stage.method->currentIndex())};
        for (int j = 0; j < 4; ++j) {
            const double value = stage.fields[j]->value();
            tokens << (value == stage.displayed[j] ? stage.stored[j] : decimal(value * units[j]));
        }
        result.insert(QString("PropStage%1").arg(i), tokens.join(' '));
    }
    return result;
}

QString ExtraPage::propagationError() const
{
    for (int i = 1; i < count->value() - 1; ++i)
        for (int j : {2, 3})
            if (stages[i].fields[j]->value() <= stages[i-1].fields[j]->value())
                return tr("The time and angle limits for stage %1 must exceed the limits for stage %2.")
                    .arg(i+1).arg(i);
    return {};
}
