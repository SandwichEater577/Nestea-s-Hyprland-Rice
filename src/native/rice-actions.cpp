// Small, synchronous desktop actions. Each installed rice-* name is a link to
// this binary; the basename chooses one operation with no shell evaluation.
#include <QCoreApplication>
#include <QDBusConnection>
#include <QDBusInterface>
#include <QDBusReply>
#include <QDBusVariant>
#include <QDateTime>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QJsonDocument>
#include <QJsonObject>
#include <QProcess>
#include <QSaveFile>
#include <QTextStream>
#include <QVariant>
#include <algorithm>
#include <QRegularExpression>

static QString home() { return QDir::homePath(); }
static QString bin(const QString &name) { return home() + "/.local/bin/" + name; }
static QString state(const QString &name) { return home() + "/.local/state/rice/" + name; }
static QString options(const QString &name) { return home() + "/.config/rice/" + name; }

static int run(const QString &program, const QStringList &args = {}) {
    return QProcess::execute(program, args);
}
static QString call(const QString &program, const QStringList &args = {}) {
    QProcess process;
    process.start(program, args);
    if (!process.waitForStarted(300) || !process.waitForFinished(1000)) {
        process.kill(); process.waitForFinished(100); return {};
    }
    return process.exitCode() == 0 ? QString::fromUtf8(process.readAllStandardOutput()).trimmed() : QString();
}
static int launch(const QString &program, const QStringList &args = {}) {
    return QProcess::startDetached(program, args) ? 0 : 1;
}
static void kick() {
    QDir().mkpath(home() + "/.local/state/rice");
    QFile file(state("status-kick"));
    if (file.open(QIODevice::WriteOnly | QIODevice::Truncate))
        file.write(QByteArray::number(QDateTime::currentMSecsSinceEpoch()));
}
static QJsonObject readObject(const QString &path) {
    QFile file(path);
    if (!file.open(QIODevice::ReadOnly)) return {};
    return QJsonDocument::fromJson(file.readAll()).object();
}
static int writeObject(const QString &path, const QJsonObject &data) {
    QDir().mkpath(QFileInfo(path).absolutePath());
    QSaveFile file(path);
    if (!file.open(QIODevice::WriteOnly)) return 1;
    file.setPermissions(QFileDevice::ReadOwner | QFileDevice::WriteOwner);
    if (file.write(QJsonDocument(data).toJson()) < 0 || !file.commit()) return 1;
    kick();
    return 0;
}
static QString player() {
    QProcess list;
    list.start("playerctl", {"-l"});
    if (!list.waitForFinished(1000) || list.exitCode()) return {};
    const auto sources = readObject(options("Media-Options.json"));
    const bool spotify = sources.value("desktop_spotify").toBool(true);
    const bool browser = sources.value("browser_media").toBool(false);
    QStringList names;
    const auto browsers = QStringList{"chromium", "chrome", "brave", "firefox", "vivaldi", "edge", "opera"};
    for (const auto &raw : QString::fromUtf8(list.readAllStandardOutput()).split('\n')) {
        const auto name = raw.trimmed();
        if ((spotify && name == "spotify") ||
            (browser && std::any_of(browsers.cbegin(), browsers.cend(),
                                    [&](const QString &b) { return name.startsWith(b, Qt::CaseInsensitive); })))
            names << name;
    }
    names.sort();
    if (spotify && names.removeOne("spotify")) names.prepend("spotify");
    for (const auto &name : names) {
        QProcess status;
        status.start("playerctl", {"--player=" + name, "status"});
        if (status.waitForFinished(700) &&
            QString::fromUtf8(status.readAllStandardOutput()).trimmed() == "Playing") return name;
    }
    return names.value(0);
}
static int media(const QString &action) {
    const auto selected = player();
    if (selected.isEmpty()) return 1;
    const QString prefix = "--player=" + selected;
    if (action == "toggle") return run("playerctl", {prefix, "play-pause"});
    if (action == "next" || action == "previous") return run("playerctl", {prefix, action});
    if (action == "up" || action == "down")
        return run("playerctl", {prefix, "volume", action == "up" ? "0.05+" : "0.05-"});
    if (action == "shuffle" || action == "repeat") {
        QProcess read;
        read.start("playerctl", {prefix, action == "shuffle" ? "shuffle" : "loop"});
        if (!read.waitForFinished(1000) || read.exitCode()) return 1;
        const auto value = QString::fromUtf8(read.readAllStandardOutput()).trimmed();
        if (action == "shuffle") return run("playerctl", {prefix, "shuffle", value == "On" ? "Off" : "On"});
        const auto next = value == "None" ? "Playlist" : value == "Playlist" ? "Track" : "None";
        return run("playerctl", {prefix, "loop", next});
    }
    return 2;
}
static int profile(const QString &name) {
    QDBusInterface properties("org.freedesktop.UPower.PowerProfiles",
                              "/org/freedesktop/UPower/PowerProfiles",
                              "org.freedesktop.DBus.Properties",
                              QDBusConnection::systemBus());
    if (!properties.isValid()) return 1;
    if (name == "current") {
        const QDBusReply<QDBusVariant> read = properties.call("Get",
            "org.freedesktop.UPower.PowerProfiles", "ActiveProfile");
        if (!read.isValid()) return 1;
        QTextStream(stdout) << read.value().variant().toString() << Qt::endl;
        return 0;
    }
    const QString target = name == "saver" ? "power-saver" :
                           name == "balanced" ? "balanced" : "performance";
    QDBusReply<void> reply = properties.call("Set", "org.freedesktop.UPower.PowerProfiles",
                                             "ActiveProfile", QVariant::fromValue(QDBusVariant(target)));
    return reply.isValid() ? 0 : 1;
}
static int audio(const QString &name) {
    const QString sink = "@DEFAULT_AUDIO_SINK@";
    const QString flag = state("audio-boost");
    if (name == "mute") return run("wpctl", {"set-mute", sink, "toggle"});
    if (name == "boost") {
        QDir().mkpath(home() + "/.local/state/rice");
        if (QFile::exists(flag)) {
            QProcess value;
            value.start("wpctl", {"get-volume", sink});
            if (value.waitForFinished(1000)) {
                const auto number = QString::fromUtf8(value.readAllStandardOutput()).split(' ').value(1).toDouble();
                if (number > 1.0 && run("wpctl", {"set-volume", sink, "1.0"})) return 1;
            }
            if (!QFile::remove(flag)) return 1;
            launch("notify-send", {"Volume ceiling: 100%"});
            return 0;
        }
        QFile file(flag);
        if (!file.open(QIODevice::WriteOnly)) return 1;
        launch("notify-send", {"Volume ceiling: 150% (boost)"});
        return 0;
    }
    return run("wpctl", {"set-volume", "-l", QFile::exists(flag) ? "1.5" : "1.0",
                         sink, name == "up" ? "3%+" : "3%-"});
}
static int brightness(const QString &name, const QStringList &args) {
    if (name == "current") {
        const auto value = call("brightnessctl", {"-m"}).split(',').value(3).remove('%');
        if (value.isEmpty()) return 1;
        QTextStream(stdout) << value << Qt::endl;
        return 0;
    }
    if (name == "set") {
        bool ok = false;
        const int value = args.value(0).toInt(&ok);
        if (!ok || value < 2 || value > 100) return 2;
        return run("brightnessctl", {"set", QString::number(value) + "%"});
    }
    return run("brightnessctl", {"set", name == "up" ? "5%+" : "5%-"});
}
static int toggleSettings() {
    return run("quickshell", {"ipc", "--path", home() + "/.local/share/rice/source/src/quickshell/shell.qml",
                              "call", "settings", "toggle"});
}
int main(int argc, char **argv) {
    QCoreApplication app(argc, argv);
    const auto command = QFileInfo(QString::fromLocal8Bit(argv[0])).fileName();
    const auto args = app.arguments().mid(1);
    int result = 2;
    if (command.startsWith("rice-audio-")) result = audio(command.mid(11));
    else if (command.startsWith("rice-media-")) result = media(command.mid(11));
    else if (command.startsWith("rice-brightness-")) result = brightness(command.mid(16), args);
    else if (command.startsWith("rice-profile-")) result = profile(command.mid(13));
    else if (command == "rice-clock-12" || command == "rice-clock-24") {
        auto value = readObject(options("settings.json"));
        value["time_format"] = command.endsWith("12") ? "12h" : "24h";
        result = writeObject(options("settings.json"), value);
    } else if (command == "rice-spotify-on" || command == "rice-spotify-off" ||
               command == "rice-browser-on" || command == "rice-browser-off") {
        auto value = readObject(options("Media-Options.json"));
        value[command.startsWith("rice-spotify") ? "desktop_spotify" : "browser_media"] =
            command.endsWith("-on");
        result = writeObject(options("Media-Options.json"), value);
    } else if (command == "rice-show-settings") result = toggleSettings();
    else if (command == "rice-show-update") {
        const auto sha = args.value(0);
        if (QRegularExpression("^[0-9a-fA-F]{12}$").match(sha).hasMatch())
            result = launch(bin("desktop-panel"), {"updates:" + sha});
    } else if (command == "rice-update-ignore") {
        const auto sha = args.value(0);
        if (QRegularExpression("^[0-9a-fA-F]{12}$").match(sha).hasMatch()) {
            auto data = readObject(state("update.json"));
            auto updates = data.value("updates").toObject();
            auto entry = updates.value(sha).toObject();
            if (!entry.isEmpty() && entry.value("kind").toString() != "mandatory") {
                entry["new"] = false;
                updates[sha] = entry;
                data["updates"] = updates;
                int count = 0;
                for (const auto &value : updates)
                    if (value.toObject().value("new").toBool() &&
                        value.toObject().value("applied").toDouble() == 0) ++count;
                data["count"] = count;
                data["available"] = count > 0;
                result = writeObject(state("update.json"), data);
            }
        }
    } else if (command == "rice-update-check") result = launch(bin("rice-update"), {"check"});
    else if (command == "rice-workspace-focus") {
        bool valid = false;
        const int workspace = args.value(0).toInt(&valid);
        if (valid && workspace >= 1 && workspace <= 99)
            result = run("hyprctl", {"dispatch", "hl.dsp.focus({workspace=" + QString::number(workspace) + "})"});
    }
    else if (command.startsWith("rice-show-")) {
        result = launch(bin("desktop-panel"), {command.mid(10)});
    } else if (command == "rice-terminal") result = launch("kitty");
    else if (command == "rice-files") result = launch("thunar");
    else if (command == "rice-wallpaper-next") result = launch(bin("change-wallpaper"));
    else if (command == "rice-screen-full" || command == "rice-screen-region")
        result = launch(bin("screenshot"), {command.endsWith("full") ? "full" : "region"});
    else if (command == "rice-lock") result = launch(bin("lock-screen"));
    else if (command == "rice-clipboard") result = launch(bin("clipboard-menu"));
    else if (command == "rice-system-monitor") result = launch("kitty", {"btop"});
    else if (command == "rice-desktop-config") result = launch("code", {home() + "/.local/share/rice/source"});
    else if (command == "rice-share-idea") result = launch("xdg-open", {
        "https://github.com/SandwichEater577/Nestea-s-Hyprland-Rice/issues/new"});
    else if (command == "rice-vscode-menu" || command == "rice-vscode-folder" ||
             command == "rice-vscode-focus")
        result = launch(bin("vscode-menu"), command.endsWith("-menu") ? QStringList{} :
                        QStringList{command.endsWith("-folder") ? "folder" : "focus"});
    if (result == 0) kick();
    else QTextStream(stderr) << command << ": action failed (" << result << ")\n";
    return result;
}
