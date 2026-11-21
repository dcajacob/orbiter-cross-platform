#include <QApplication>
#include <QCheckBox>
#include <QFile>
#include <QGenericPlugin>
#include <QLabel>
#include <QPushButton>
#include <QSettings>
#include <QTimer>
#include <QTreeWidget>

static void logLine(const QString &line) {
    QFile output(qEnvironmentVariable("ORBITER_GUI_RECEIPT"));
    if (output.open(QIODevice::WriteOnly | QIODevice::Append))
        output.write(line.toUtf8() + "\n");
}
class ReadOnlyProbe : public QGenericPlugin {
    Q_OBJECT
    Q_PLUGIN_METADATA(IID QGenericPluginFactoryInterface_iid FILE "keys.json")
public:
    QObject *create(const QString &, const QString &) override {
        QTimer::singleShot(600, []{
            QWidget *window = nullptr;
            for (auto w : QApplication::topLevelWidgets())
                if (w->objectName() == "launchpad") window = w;
            if (!window) { logLine("driver-error=no launchpad"); qApp->exit(41); return; }
            auto tree = window->findChild<QTreeWidget*>("scenarioTree");
            auto launch = window->findChild<QPushButton*>("launchButton");
            auto status = window->findChild<QLabel*>("launchStatus");
            if (!tree || !launch || !status) { logLine("driver-error=missing controls"); qApp->exit(42); return; }
            logLine("initial-selection=" + (tree->currentItem() ? tree->currentItem()->text(0) : QString()));
            QCheckBox *paused=nullptr;
            for (auto c : window->findChildren<QCheckBox*>()) if (c->text().contains("Start paused",Qt::CaseInsensitive) && c->isVisible()) paused=c;
            if (paused) logLine(QString("initial-paused=") + (paused->isChecked() ? "yes" : "no"));
            const QString phase=qEnvironmentVariable("ORBITER_GUI_PHASE");
            if (phase=="settings") { qApp->quit(); return; }
            if (phase=="first" && paused && paused->isChecked()) { paused->click(); logLine("set-paused=no"); }
            auto name=qEnvironmentVariable("ORBITER_GUI_SCENARIO");
            auto entries=tree->findItems(name,Qt::MatchExactly|Qt::MatchRecursive);
            if(entries.size()!=1) { logLine("driver-error=scenario matches " + QString::number(entries.size())); qApp->exit(43); return; }
            tree->setCurrentItem(entries.first());
            if(!launch->isEnabled()) { logLine("launch-disabled="+status->text()); qApp->quit(); return; }
            launch->click();
            logLine("requested="+name);
            auto timer=new QTimer(window);
            QObject::connect(timer,&QTimer::timeout,window,[window,status,previous=QString()]() mutable {
                auto value=window->isVisible() ? status->text() : QString("launcher-hidden");
                if(value!=previous) { logLine("flight="+value); previous=value; }
                if (value.startsWith("Orbiter could not") || value.startsWith("Session ended") || value.startsWith("Orbiter closed") || value.startsWith("Orbiter exited")) qApp->quit();
            });
            timer->start(100);
        });
        return new QObject(this);
    }
};
#include "probe.moc"
