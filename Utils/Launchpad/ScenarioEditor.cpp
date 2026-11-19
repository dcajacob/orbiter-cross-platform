#include "ScenarioEditor.h"

#include <QComboBox>
#include <QCoreApplication>
#include <QDateTimeEdit>
#include <QDialog>
#include <QDialogButtonBox>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QFormLayout>
#include <QLabel>
#include <QLineEdit>
#include <QMap>
#include <QRegularExpression>
#include <QSet>
#include <QStackedWidget>
#include <QTemporaryFile>
#include <QTimeZone>
#include <QVBoxLayout>

#include <cmath>
#include <stdexcept>

namespace {
constexpr double UnixEpochMjd = 40587.0;
constexpr double MillisecondsPerDay = 86400000.0;

QString tr(const char *message)
{
    return QCoreApplication::translate("ScenarioEditor", message);
}

[[noreturn]] void fail(const QString &message)
{
    throw std::runtime_error(message.toUtf8().constData());
}

QByteArray contents(const QByteArray &line)
{
    const auto comment = line.indexOf(';');
    return (comment < 0 ? line : line.left(comment)).trimmed();
}

QByteArray field(const QByteArray &line)
{
    return contents(line).simplified().split(' ').constFirst().toUpper();
}

QByteArray value(const QByteArray &line)
{
    const auto trimmed = contents(line);
    return trimmed.mid(field(line).size()).trimmed();
}

bool isInside(const QString &root, const QString &path)
{
    if (root.isEmpty() || path.isEmpty())
        return false;
    const auto relative = QDir(root).relativeFilePath(path);
    return relative != "." && relative != ".." && !relative.startsWith("../")
        && !QDir::isAbsolutePath(relative);
}

struct Vessel {
    QByteArray name;
    qsizetype begin;
    qsizetype end;
    QMap<QByteArray, QByteArray> fields;

    bool landed() const { return fields.value("STATUS").simplified().toUpper().startsWith("LANDED "); }

    QString referenceBody() const
    {
        const auto status = fields.value("STATUS").simplified();
        return QString::fromUtf8(status.mid(status.indexOf(' ') + 1));
    }

    bool cartesian() const
    {
        return fields.value("STATUS").simplified().toUpper().startsWith("ORBITING ")
            && !fields.contains("ELEMENTS") && fields.contains("RPOS") && fields.contains("RVEL");
    }
};

class Scenario {
public:
    explicit Scenario(const QByteArray &source)
        : lines(source.split('\n')), newline(source.contains("\r\n") ? "\r" : "")
    {
        const auto environment = section("BEGIN_ENVIRONMENT", "END_ENVIRONMENT");
        const auto ships = section("BEGIN_SHIPS", "END_SHIPS");
        for (auto row = environment.first + 1; row < environment.second; ++row) {
            if (field(lines[row]) == "PLAYBACK")
                fail(tr("This scenario uses recorded playback. Choose a live scenario to change its starting state."));
            if (field(lines[row]) == "DATE") {
                if (dateLine != -1)
                    fail(tr("The scenario has more than one start date."));
                dateLine = row;
                const auto tokens = value(lines[row]).simplified().split(' ');
                bool ok = false;
                const double time = tokens.value(1).toDouble(&ok);
                const auto format = tokens.value(0).toUpper();
                if (!ok || !std::isfinite(time) || (format != "MJD" && format != "JD" && format != "JE"))
                    fail(tr("The scenario's start date could not be read."));
                mjd = format == "JD" ? time - 2400000.5
                    : format == "JE" ? (time - 2000.0) * 365.25 + 51544.5 : time;
            }
        }
        if (dateLine == -1)
            dateLine = environment.second;

        QSet<QByteArray> linked;
        for (auto row = ships.first + 1; row < ships.second;) {
            const auto header = contents(lines[row]);
            if (header.isEmpty()) {
                ++row;
                continue;
            }
            Vessel vessel{header.split(':').constFirst().trimmed(), row++, 0, {}};
            for (; row < ships.second && contents(lines[row]).toUpper() != "END"; ++row) {
                const auto key = field(lines[row]);
                const auto data = value(lines[row]);
                if (key == "FLIGHTDATA")
                    fail(tr("This scenario uses recorded playback. Choose a live scenario to change its starting state."));
                if (key == "ATTACHED" || key == "DOCKINFO") {
                    for (const auto &link : data.simplified().split(' ')) {
                        const auto comma = link.indexOf(',');
                        if (comma >= 0 && comma + 1 < link.size()) {
                            linked.insert(vessel.name.toLower());
                            linked.insert(link.mid(comma + 1).toLower());
                        }
                    }
                }
                vessel.fields.insert(key, data);
            }
            if (row == ships.second)
                fail(tr("A vessel is missing its END line."));
            vessel.end = row++;
            if (vessel.landed() || vessel.cartesian())
                movable.append(vessel);
        }
        movable.removeIf([&](const Vessel &vessel) { return linked.contains(vessel.name.toLower()); });
    }

    QByteArray edited(bool changeDate, double newMjd, int index,
                      const QByteArray &position, const QByteArray &direction) const
    {
        auto result = lines;
        auto dateRow = dateLine;
        if (index >= 0) {
            // Keep the vessel class, reference body and module state. Let Orbiter
            // compute touchdown attitude and height for a new ground location.
            const auto &vessel = movable[index];
            for (auto row = vessel.end - 1; row > vessel.begin; --row) {
                const auto key = field(result[row]);
                if (vessel.landed() && (key == "BASE" || key == "POS" || key == "HEADING"
                                         || key == "ALT" || key == "AROT" || key == "VROT")) {
                    result.removeAt(row);
                } else if (!vessel.landed() && (key == "RPOS" || key == "RVEL")) {
                    replace(result[row], key + ' ' + (key == "RPOS" ? position : direction));
                }
            }
            if (vessel.landed()) {
                auto status = vessel.begin + 1;
                while (field(result[status]) != "STATUS")
                    ++status;
                result.insert(status + 1, "  HEADING " + direction + newline);
                result.insert(status + 1, "  POS " + position + newline);
            }
            if (dateLine > vessel.end)
                dateRow += result.size() - lines.size();
        }
        if (changeDate) {
            const auto date = "Date MJD " + QByteArray::number(newMjd, 'f', 11);
            if (field(lines[dateLine]) == "DATE")
                replace(result[dateRow], date);
            else
                result.insert(dateRow, "  " + date + newline);
        }
        return result.join('\n');
    }

    QList<Vessel> movable;
    double mjd = 51982.5; // Native host default for scenarios without a Date.

private:
    QPair<qsizetype, qsizetype> section(const QByteArray &begin, const QByteArray &end) const
    {
        qsizetype start = -1;
        for (qsizetype i = 0; i < lines.size(); ++i) {
            const auto token = contents(lines[i]).toUpper();
            if (token == begin)
                start = i;
            else if (start >= 0 && token == end)
                return {start, i};
        }
        fail(tr("Expected a complete %1 section.").arg(QString::fromLatin1(begin.mid(6))));
    }

    static void replace(QByteArray &line, const QByteArray &replacement)
    {
        const auto first = line.indexOf(contents(line));
        const auto suffix = line.indexOf(';');
        const auto ending = line.endsWith('\r') ? QByteArray("\r") : QByteArray();
        line = line.left(first) + replacement + (suffix >= 0 ? " " + line.mid(suffix) : ending);
    }

    QList<QByteArray> lines;
    QByteArray newline;
    qsizetype dateLine = -1;
};

QByteArray coordinates(const QLineEdit *input, int size)
{
    const auto parts = input->text().simplified().split(' ', Qt::SkipEmptyParts);
    if (parts.size() != size)
        fail(tr("Enter %1 numbers separated by spaces.").arg(size));
    QByteArray result;
    for (const auto &part : parts) {
        bool ok = false;
        const double number = part.toDouble(&ok);
        if (!ok || !std::isfinite(number))
            fail(tr("Use finite numbers with a decimal point."));
        if (!result.isEmpty())
            result += ' ';
        result += QByteArray::number(number, 'g', 16);
    }
    return result;
}
}

QString copyStockScenario(QWidget *parent, const QString &source, const QString &stockRoot,
                          const QString &saveRoot)
{
    const auto stock = QFileInfo(stockRoot).canonicalFilePath();
    const auto file = QFileInfo(source);
    if (!file.isFile() || !isInside(stock, file.canonicalFilePath()))
        fail(tr("Select a stock scenario to copy."));
    QFile input(source);
    if (!input.open(QIODevice::ReadOnly))
        fail(tr("Could not read the stock scenario: %1").arg(input.errorString()));
    const auto data = input.readAll();
    if (input.error() != QFileDevice::NoError)
        fail(tr("Could not read the stock scenario: %1").arg(input.errorString()));
    const Scenario scenario(data);

    QDialog dialog(parent);
    dialog.setWindowTitle(tr("Copy and edit scenario"));
    dialog.resize(540, 0);
    auto *layout = new QVBoxLayout(&dialog);
    auto *form = new QFormLayout;
    layout->addLayout(form);
    auto *name = new QLineEdit(file.completeBaseName() + tr(" (copy)"));
    name->setObjectName("scenarioCopyName");
    name->selectAll();
    form->addRow(tr("&Copy name"), name);

    const QDate start(1, 1, 1), end(9999, 12, 31);
    const double epochMs = (scenario.mjd - UnixEpochMjd) * MillisecondsPerDay;
    const auto utc = QTimeZone::utc();
    const auto minimum = QDateTime(start, QTime(0, 0), utc);
    const auto maximum = QDateTime(end, QTime(23, 59, 59), utc);
    if (epochMs < minimum.toMSecsSinceEpoch() || epochMs > maximum.toMSecsSinceEpoch())
        fail(tr("The start date is outside the date editor's range."));
    auto *date = new QDateTimeEdit;
    date->setObjectName("scenarioStartDate");
#if QT_VERSION >= QT_VERSION_CHECK(6, 7, 0)
    date->setTimeZone(utc);
#else
    date->setTimeSpec(Qt::UTC);
#endif
    date->setDateTimeRange(minimum, maximum);
    date->setDisplayFormat("yyyy-MM-dd HH:mm:ss");
    date->setCalendarPopup(true);
    date->setDateTime(QDateTime::fromMSecsSinceEpoch(std::llround(epochMs), utc));
    const auto originalDate = date->dateTime();
    form->addRow(tr("Start &date (UTC)"), date);

    auto *vessels = new QComboBox;
    vessels->setObjectName("scenarioVessel");
    vessels->addItem(tr("Keep vessel positions"));
    for (const auto &vessel : scenario.movable)
        vessels->addItem(QString::fromUtf8(vessel.name));
    form->addRow(tr("&Vessel to move"), vessels);

    auto *placement = new QStackedWidget;
    layout->addWidget(placement);
    const auto note = [](const QString &text) {
        auto *label = new QLabel(text);
        label->setWordWrap(true);
        return label;
    };
    placement->addWidget(note(tr("Move a landed vessel or one with a position and velocity. Docked and attached vessels keep their placement.")));
    auto *ground = new QWidget;
    auto *groundForm = new QFormLayout(ground);
    auto *longitude = new QLineEdit;
    auto *latitude = new QLineEdit;
    auto *heading = new QLineEdit;
    longitude->setObjectName("scenarioLongitude");
    latitude->setObjectName("scenarioLatitude");
    heading->setObjectName("scenarioHeading");
    groundForm->addRow(tr("&Longitude (° east)"), longitude);
    groundForm->addRow(tr("L&atitude (° north)"), latitude);
    groundForm->addRow(tr("&Heading (°)"), heading);
    auto *groundHint = note({});
    groundForm->addRow(groundHint);
    placement->addWidget(ground);
    auto *orbit = new QWidget;
    auto *orbitForm = new QFormLayout(orbit);
    auto *position = new QLineEdit;
    auto *velocity = new QLineEdit;
    position->setObjectName("scenarioPosition");
    velocity->setObjectName("scenarioVelocity");
    orbitForm->addRow(tr("&Position X Y Z (m)"), position);
    orbitForm->addRow(tr("&Velocity X Y Z (m/s)"), velocity);
    auto *orbitHint = note({});
    orbitForm->addRow(orbitHint);
    placement->addWidget(orbit);

    QObject::connect(vessels, &QComboBox::currentIndexChanged, &dialog, [&](int index) {
        if (index == 0) {
            placement->setCurrentIndex(0);
            return;
        }
        const auto &vessel = scenario.movable[index - 1];
        if (vessel.landed()) {
            const auto coordinates = vessel.fields.contains("BASE") ? QList<QByteArray>{}
                : vessel.fields.value("POS").simplified().split(' ');
            longitude->setText(QString::fromLatin1(coordinates.value(0)));
            latitude->setText(QString::fromLatin1(coordinates.value(1)));
            heading->setText(QString::fromLatin1(vessel.fields.value("HEADING", "0")));
            groundHint->setText(tr("The vessel starts on the surface of %1.").arg(vessel.referenceBody()));
            placement->setCurrentWidget(ground);
        } else {
            position->setText(QString::fromLatin1(vessel.fields.value("RPOS")));
            velocity->setText(QString::fromLatin1(vessel.fields.value("RVEL")));
            orbitHint->setText(tr("Vectors use Orbiter's ecliptic axes relative to %1.").arg(vessel.referenceBody()));
            placement->setCurrentWidget(orbit);
        }
    });

    auto *error = note({});
    error->setObjectName("scenarioCopyError");
    error->setTextFormat(Qt::PlainText);
    error->hide();
    layout->addWidget(error);
    auto *buttons = new QDialogButtonBox(QDialogButtonBox::Save | QDialogButtonBox::Cancel);
    layout->addWidget(buttons);
    QString destination;
    QObject::connect(buttons, &QDialogButtonBox::rejected, &dialog, &QDialog::reject);
    QObject::connect(buttons, &QDialogButtonBox::accepted, &dialog, [&] {
        try {
            auto stem = name->text().trimmed();
            if (stem.endsWith(".scn", Qt::CaseInsensitive))
                stem.chop(4);
            static const QRegularExpression invalidName(R"([\x{0000}-\x{001f}<>:"/\\|?*])");
            if (stem.isEmpty() || stem.endsWith('.') || stem.contains(invalidName))
                fail(tr("Enter a valid file name without folders."));
            if (stem.compare("Quicksave", Qt::CaseInsensitive) == 0)
                fail(tr("Choose a different name. Orbiter uses Quicksave for in-flight saves."));
            const int index = vessels->currentIndex() - 1;
            QByteArray location, direction;
            if (index >= 0) {
                if (scenario.movable[index].landed()) {
                    const auto lng = coordinates(longitude, 1);
                    const auto lat = coordinates(latitude, 1);
                    direction = coordinates(heading, 1);
                    if (std::abs(lng.toDouble()) > 180 || std::abs(lat.toDouble()) > 90
                        || direction.toDouble() < 0 || direction.toDouble() >= 360)
                        fail(tr("Use longitude −180 to 180, latitude −90 to 90, and heading 0 to under 360."));
                    location = lng + ' ' + lat;
                } else {
                    location = coordinates(position, 3);
                    direction = coordinates(velocity, 3);
                    if (location == "0 0 0")
                        fail(tr("Position must be outside the center of the reference body."));
                }
            }
            const auto copy = scenario.edited(date->dateTime() != originalDate,
                UnixEpochMjd + date->dateTime().toMSecsSinceEpoch() / MillisecondsPerDay,
                index, location, direction);
            if (saveRoot.isEmpty() || !QDir().mkpath(saveRoot))
                fail(tr("Could not create the saved scenarios folder."));
            const auto saved = QFileInfo(saveRoot).canonicalFilePath();
            if (saved.isEmpty() || saved == stock || isInside(stock, saved))
                fail(tr("Choose a saved scenarios folder outside the stock scenarios."));
            const auto target = QDir(saved).filePath(stem + ".scn");
            if (QFileInfo::exists(target))
                fail(tr("That scenario name already exists. Choose a different name."));
            QTemporaryFile temporary(QDir(saved).filePath(".scenario-copy-XXXXXX"));
            if (!temporary.open() || temporary.write(copy) != copy.size() || !temporary.flush()
                || !temporary.rename(target))
                fail(tr("Could not save the scenario copy: %1").arg(temporary.errorString()));
            temporary.setAutoRemove(false);
            destination = QDir(saveRoot).filePath(stem + ".scn");
            dialog.accept();
        } catch (const std::exception &failure) {
            error->setText(QString::fromUtf8(failure.what()));
            error->show();
        }
    });
    dialog.exec();
    return destination;
}
