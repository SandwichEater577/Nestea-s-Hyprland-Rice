// Long-lived status stream for QuickShell. Slow device queries run in worker
// threads; each tier emits changed fields as soon as they are ready.
#include <QCoreApplication>
#include <QCryptographicHash>
#include <QDir>
#include <QDirIterator>
#include <QDateTime>
#include <QFile>
#include <QFileInfo>
#include <QFileSystemWatcher>
#include <QFutureWatcher>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QProcess>
#include <QSet>
#include <QTextStream>
#include <QTimer>
#include <QtConcurrent>
#include <algorithm>

static QString home() { return QDir::homePath(); }
static QString readFile(const QString &path) {
    QFile file(path);
    return file.open(QIODevice::ReadOnly) ? QString::fromUtf8(file.readAll()).trimmed() : QString();
}
static QString call(const QString &program, const QStringList &args, int timeout = 900) {
    QProcess process;
    process.start(program, args);
    if (!process.waitForStarted(300) || !process.waitForFinished(timeout)) {
        process.kill();
        process.waitForFinished(100);
        return {};
    }
    return process.exitCode() == 0 ? QString::fromUtf8(process.readAllStandardOutput()).trimmed() : QString();
}
static QJsonObject mediaOptions() {
    return QJsonDocument::fromJson(readFile(home() + "/.config/rice/Media-Options.json").toUtf8()).object();
}
static QString selectedPlayer() {
    const auto opts = mediaOptions();
    const bool spotify = opts.value("desktop_spotify").toBool(true);
    const bool browser = opts.value("browser_media").toBool(false);
    const QStringList browsers{"chromium", "brave", "chrome", "firefox", "vivaldi", "edge", "opera"};
    QStringList names;
    for (const auto &name : call("playerctl", {"-l"}).split('\n', Qt::SkipEmptyParts)) {
        if ((spotify && name == "spotify") ||
            (browser && std::any_of(browsers.cbegin(), browsers.cend(),
                        [&](const QString &prefix) { return name.startsWith(prefix, Qt::CaseInsensitive); })))
            names << name;
    }
    names.sort();
    if (spotify && names.removeOne("spotify")) names.prepend("spotify");
    for (const auto &name : names)
        if (call("playerctl", {"--player=" + name, "status"}) == "Playing") return name;
    return names.value(0);
}
static QJsonObject audio() {
    const QString value = call("wpctl", {"get-volume", "@DEFAULT_AUDIO_SINK@"});
    const bool boosted = QFile::exists(home() + "/.local/state/rice/audio-boost");
    bool valid = false;
    const int percent = qRound(value.split(' ', Qt::SkipEmptyParts).value(1).toDouble(&valid) * 100);
    const bool muted = value.contains("MUTED");
    const QString text = valid ? QString(muted ? "󰝟  " : "  ") +
                                   QString::number(percent) + "%" + (boosted ? " +" : "")
                               : "󰝟 —";
    const QString tip = valid ?
        QString(boosted ? "Middle click or F4: lock to 100%" : "Middle click or F4: unlock 150%") +
        "\nWheel up/down: volume · Left click: mute\nRight click: output and application volume"
        : "No audio output";
    return {{"audio", text}, {"audio_tooltip", tip}};
}
static QJsonObject battery() {
    const QDir supply("/sys/class/power_supply");
    const auto batteries = supply.entryList({"BAT*"}, QDir::Dirs | QDir::NoDotAndDotDot);
    if (batteries.isEmpty()) return {{"battery", ""}, {"battery_icon", ""}, {"battery_tooltip", ""}};
    const QString base = supply.filePath(batteries.first()) + "/";
    bool valid = false;
    const int percent = readFile(base + "capacity").toInt(&valid);
    if (!valid) return {{"battery", ""}, {"battery_icon", ""}, {"battery_tooltip", ""}};
    const QString status = readFile(base + "status");
    const QStringList icons{"", "", "", "", ""};
    const QString icon = status == "Charging" ? "" : status == "Full" ? "" :
                         icons.value(qBound(0, percent / 20, 4));
    QString tip = "Battery · " + QString::number(percent) + "%\n" + status;
    const auto seconds = readFile(base + (status == "Charging" ? "time_to_full_now" : "time_to_empty_now")).toInt();
    if (seconds > 0) tip += QString("\n%1h %2m remaining").arg(seconds / 3600).arg((seconds / 60) % 60);
    return {{"battery", QString::number(percent) + "%"}, {"battery_icon", icon}, {"battery_tooltip", tip}};
}
static QJsonObject media() {
    const auto name = selectedPlayer();
    if (name.isEmpty()) return {{"spotify", ""}, {"spotify_running", false}, {"cover", ""},
                                {"track", ""}, {"repeat", ""}, {"repeat_tooltip", ""},
                                {"shuffle", ""}, {"shuffle_tooltip", ""}};
    const QString prefix = "--player=" + name;
    const bool playing = call("playerctl", {prefix, "status"}) == "Playing";
    const auto shuffle = call("playerctl", {prefix, "shuffle"});
    const auto loop = call("playerctl", {prefix, "loop"});
    const auto details = call("playerctl", {prefix, "metadata", "--format",
                              "{{mpris:artUrl}}\t{{artist}}\t{{title}}"}, 1200).split('\t');
    const QString art = details.value(0);
    QString cover;
    if (art.startsWith("file:")) cover = art;
    else if (art.startsWith("https:") || art.startsWith("http:")) {
        const QString cached = home() + "/.cache/rice-media-covers/" +
            QString::fromLatin1(QCryptographicHash::hash(art.toUtf8(), QCryptographicHash::Sha256).toHex()) + ".art";
        cover = QFile::exists(cached) ? "file://" + cached : art;
    }
    const QString track = (details.value(1) + " — " + details.value(2)).trimmed();
    const bool hasShuffle = shuffle == "On" || shuffle == "Off";
    const bool hasLoop = loop == "None" || loop == "Playlist" || loop == "Track";
    return {{"spotify", playing ? "" : ""}, {"spotify_running", true},
            {"cover", cover}, {"track", cover.isEmpty() ? "" : track},
            {"shuffle", hasShuffle ? "" : ""},
            {"shuffle_tooltip", hasShuffle ?
                (shuffle == "On" ? "Shuffle on (regular / Smart not exposed)" : "Shuffle off") +
                QString("\nClick: toggle shuffle\nRight-click: choose Smart Shuffle in Spotify") : ""},
            {"repeat", hasLoop ? (loop == "Track" ? "󰑘" : "") : ""},
            {"repeat_tooltip", hasLoop ?
                (loop == "Track" ? "Repeat one" : loop == "Playlist" ? "Repeat all" : "Repeat off") +
                QString("\nClick: off → all → one") : ""}};
}
static QJsonObject displayBluetooth() {
    QString display, tip;
    const auto monitors = QJsonDocument::fromJson(call("hyprctl", {"-j", "monitors", "all"}).toUtf8()).array();
    QStringList names;
    for (const auto &item : monitors) {
        const auto monitor = item.toObject();
        const auto output = monitor.value("name").toString();
        if (!output.startsWith("eDP-") && !output.startsWith("LVDS-") &&
            !output.startsWith("DSI-"))
            names << monitor.value("model").toString(output);
    }
    if (!names.isEmpty()) {
        display = "󰍹";
        tip = "Displays · " + names.join(", ") + "\nClick to change layout";
    }
    const auto blue = call("bluetoothctl", {"show"});
    return {{"display", display}, {"display_tooltip", tip},
            {"bluetooth", blue.contains("Powered: yes") ? "" : blue.isEmpty() ? "" : "󰂲"}};
}
static QJsonObject network() {
    const auto raw = call("nmcli", {"-t", "-f",
        "GENERAL.DEVICE,GENERAL.TYPE,GENERAL.STATE,GENERAL.CONNECTION,IP4.ADDRESS", "device", "show"}, 1600);
    QString device, kind, name, address;
    for (const auto &block : raw.split("\n\n")) {
        QString candidate, type, connection, ip, status;
        for (const auto &line : block.split('\n')) {
            const int at = line.indexOf(':');
            if (at < 0) continue;
            const auto key = line.left(at);
            const auto value = line.mid(at + 1).replace("\\:", ":");
            if (key == "GENERAL.DEVICE") candidate = value;
            else if (key == "GENERAL.TYPE") type = value;
            else if (key == "GENERAL.STATE") status = value;
            else if (key == "GENERAL.CONNECTION") connection = value;
            else if (key.startsWith("IP4.ADDRESS[")) ip = value;
        }
        if ((type == "wifi" || type == "ethernet") && status.startsWith("100")) {
            if (device.isEmpty() || type == "ethernet") {
                device = candidate; kind = type; name = connection; address = ip;
            }
        }
    }
    if (device.isEmpty()) return {{"network", "󰖪"}, {"network_tooltip", "No internet\nRight-click: networks"}};
    static QString previousDevice;
    static qint64 previousBytes = 0, previousMs = 0;
    const qint64 bytes = readFile("/sys/class/net/" + device + "/statistics/rx_bytes").toLongLong();
    const qint64 now = QDateTime::currentMSecsSinceEpoch();
    const double rate = device == previousDevice && now > previousMs + 100 ?
        std::max(0.0, (bytes - previousBytes) * 1000.0 / (now - previousMs) / 1000000.0) : 0.0;
    previousDevice = device; previousBytes = bytes; previousMs = now;
    const auto connectivity = call("nmcli", {"networking", "connectivity"});
    QString signal;
    if (kind == "wifi") {
        for (const auto &line : call("nmcli", {"-t", "-f", "IN-USE,SIGNAL", "device", "wifi",
                                             "list", "--rescan", "no", "ifname", device}).split('\n'))
            if (line.startsWith("*:")) { signal = line.mid(2) + "% "; break; }
    }
    const auto icon = connectivity == "none" || connectivity == "limited" || connectivity == "portal" ?
                      "󰖪" : kind == "ethernet" ? "󰈀" : "";
    return {{"network", QString("%1  %2 ↓  %3 MB/s").arg(icon, signal).arg(rate, 0, 'f', 2)},
            {"network_tooltip", QString("%1 · %2\n%3\nInternet: %4\nRight-click: networks and diagnostics")
                                    .arg(name, device, address, connectivity)}};
}
class Stream : public QObject {
    QJsonObject latest;
    QSet<QString> running;
public:
    explicit Stream(QObject *parent = nullptr) : QObject(parent) {}
    void schedule(const QString &tier, QJsonObject (*reader)()) {
        if (running.contains(tier)) return;
        running.insert(tier);
        auto *watch = new QFutureWatcher<QJsonObject>(this);
        connect(watch, &QFutureWatcher<QJsonObject>::finished, this, [this, watch, tier] {
            running.remove(tier);
            const auto fields = watch->result();
            QJsonObject changed;
            for (auto it = fields.begin(); it != fields.end(); ++it)
                if (latest.value(it.key()) != it.value()) {
                    latest.insert(it.key(), it.value());
                    changed.insert(it.key(), it.value());
                }
            if (!changed.isEmpty())
                QTextStream(stdout) << QJsonDocument(changed).toJson(QJsonDocument::Compact) << Qt::endl;
            watch->deleteLater();
        });
        watch->setFuture(QtConcurrent::run(reader));
    }
};
int main(int argc, char **argv) {
    QCoreApplication app(argc, argv);
    Stream stream;
    const auto args = app.arguments();
    if (args.contains("--once")) {
        QJsonObject all;
        for (const auto &part : {audio(), battery(), media(), network(), displayBluetooth()})
            for (auto it = part.begin(); it != part.end(); ++it) all.insert(it.key(), it.value());
        QTextStream(stdout) << QJsonDocument(all).toJson(QJsonDocument::Compact) << Qt::endl;
        return 0;
    }
    auto *fast = new QTimer(&app), *song = new QTimer(&app), *net = new QTimer(&app),
         *slow = new QTimer(&app), *power = new QTimer(&app);
    QObject::connect(fast, &QTimer::timeout, &app, [&] { stream.schedule("audio", audio); });
    QObject::connect(song, &QTimer::timeout, &app, [&] { stream.schedule("media", media); });
    QObject::connect(net, &QTimer::timeout, &app, [&] { stream.schedule("network", network); });
    QObject::connect(slow, &QTimer::timeout, &app, [&] { stream.schedule("slow", displayBluetooth); });
    QObject::connect(power, &QTimer::timeout, &app, [&] { stream.schedule("battery", battery); });
    fast->start(750); song->start(1500); net->start(3000); slow->start(10000); power->start(5000);
    stream.schedule("audio", audio);
    stream.schedule("battery", battery);
    stream.schedule("media", media);
    stream.schedule("network", network);
    stream.schedule("slow", displayBluetooth);
    const QString kick = home() + "/.local/state/rice/status-kick";
    QDir().mkpath(QFileInfo(kick).absolutePath());
    if (!QFile::exists(kick)) {
        QFile file(kick);
        if (!file.open(QIODevice::WriteOnly))
            QTextStream(stderr) << "Cannot create status kick file: " << kick << Qt::endl;
    }
    QFileSystemWatcher watcher({kick}, &app);
    QObject::connect(&watcher, &QFileSystemWatcher::fileChanged, &app, [&] {
        stream.schedule("audio", audio); stream.schedule("media", media);
        stream.schedule("network", network); stream.schedule("battery", battery);
        if (!watcher.files().contains(kick)) watcher.addPath(kick);
    });
    return app.exec();
}
