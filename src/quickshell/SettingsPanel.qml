import QtQuick
import QtQuick.Controls as Controls
import Quickshell
import Quickshell.Io

PopupWindow {
    id: panel
    property Item trigger
    property bool shown: false
    property bool nativeReady: false
    property bool devEnabled: false
    property string profile: ""
    property int brightnessValue: 50
    property bool brightnessAvailable: false
    property bool spotifyEnabled: true
    property bool browserEnabled: false
    property string clockFormat: "24h"
    property var updateState: ({})
    property var pendingUpdate: newestUpdate()
    signal closeRequested()

    Process {
        command: ["test", "-f", Quickshell.env("HOME") + "/.local/share/rice/source/dev/dev-options.py"]
        running: true
        onExited: (code) => panel.devEnabled = code === 0
    }

    anchor.item: trigger
    anchor.rect.x: trigger ? trigger.width - width : 0
    anchor.rect.y: trigger ? trigger.height + 8 : 0
    implicitWidth: 392
    implicitHeight: Math.min(790, screen ? screen.height - 54 : 790)
    color: "transparent"
    visible: shown
    grabFocus: true
    onVisibleChanged: {
        if (visible) {
            profileRead.running = true
            brightnessRead.running = true
            updateFile.reload()
        } else if (shown) closeRequested()
    }
    function executable(name, args) {
        var home = Quickshell.env("HOME")
        if (nativeReady) {
            Quickshell.execDetached([home + "/.local/bin/" + name].concat(args || []))
            return
        }
        var command = []
        if (name.indexOf("rice-profile-") === 0)
            command = ["tlpctl", "set", name === "rice-profile-saver" ? "power-saver" : name === "rice-profile-fast" ? "performance" : "balanced"]
        else if (name === "rice-brightness-set") command = ["brightnessctl", "set", args[0] + "%"]
        else if (name === "rice-clock-12" || name === "rice-clock-24")
            command = [home + "/.local/bin/rice-clock", "set", name.endsWith("12") ? "12h" : "24h"]
        else if (name.indexOf("rice-spotify-") === 0 || name.indexOf("rice-browser-") === 0)
            command = [home + "/.local/bin/rice-media", "set", name.indexOf("rice-spotify-") === 0 ? "desktop_spotify" : "browser_media", name.endsWith("-on") ? "on" : "off"]
        else if (name === "rice-update-check") command = [home + "/.local/bin/rice-update", "check"]
        else if (name === "rice-update-ignore") command = [home + "/.local/share/rice/source/src/bin/rice-update", "ignore", args[0]]
        else if (name === "rice-show-update") command = [home + "/.local/bin/desktop-panel", "updates"]
        else if (name.indexOf("rice-show-") === 0) command = [home + "/.local/bin/desktop-panel", name.slice(10)]
        else if (name === "rice-system-monitor") command = ["kitty", "btop"]
        else if (name === "rice-desktop-config") command = ["code", home + "/.local/share/rice/source"]
        else if (name === "rice-share-idea") command = ["xdg-open", "https://github.com/SandwichEater577/Nestea-s-Hyprland-Rice/issues/new"]
        if (command.length) Quickshell.execDetached(command)
    }
    function newestUpdate() {
        var updates = updateState.updates || {}
        var keys = Object.keys(updates).filter(k => updates[k].new && !updates[k].applied)
        keys.sort((a, b) => (updates[b].kind === "mandatory" ? 1 : 0) -
                           (updates[a].kind === "mandatory" ? 1 : 0) ||
                           (updates[b].when || 0) - (updates[a].when || 0))
        return keys.length ? ({sha: keys[0], detail: updates[keys[0]].summary || "Rice update",
                               kind: updates[keys[0]].kind || "recommended", count: keys.length}) : null
    }
    function openPage(page) {
        closeRequested()
        executable("rice-show-" + page)
    }
    function setProfile(value) {
        profile = value
        executable(value === "power-saver" ? "rice-profile-saver" :
                   value === "balanced" ? "rice-profile-balanced" : "rice-profile-fast")
        profileRefresh.restart()
    }

    Process {
        id: profileRead
        command: panel.nativeReady ? [Quickshell.env("HOME") + "/.local/bin/rice-profile-current"] : ["tlpctl", "get"]
        stdout: SplitParser { onRead: line => panel.profile = line.trim() }
    }
    Process {
        id: brightnessRead
        command: panel.nativeReady ? [Quickshell.env("HOME") + "/.local/bin/rice-brightness-current"] : ["brightnessctl", "-m"]
        stdout: SplitParser {
            onRead: line => {
                var value = Number(panel.nativeReady ? line.trim() : (line.split(",")[3] || "").replace("%", ""))
                if (!isNaN(value) && value >= 2 && value <= 100) {
                    panel.brightnessValue = value
                    panel.brightnessAvailable = true
                }
            }
        }
    }
    Timer { id: profileRefresh; interval: 160; onTriggered: profileRead.running = true }
    Timer {
        id: brightnessCommit
        interval: 90
        onTriggered: panel.executable("rice-brightness-set", [String(panel.brightnessValue)])
    }
    FileView {
        path: Quickshell.env("HOME") + "/.config/rice/settings.json"
        watchChanges: true
        blockLoading: true
        onFileChanged: reload()
        onTextChanged: {
            try { panel.clockFormat = JSON.parse(text()).time_format === "12h" ? "12h" : "24h" } catch (e) {}
        }
    }
    FileView {
        path: Quickshell.env("HOME") + "/.config/rice/Media-Options.json"
        watchChanges: true
        blockLoading: true
        onFileChanged: reload()
        onTextChanged: {
            try {
                var data = JSON.parse(text())
                panel.spotifyEnabled = data.desktop_spotify !== false
                panel.browserEnabled = data.browser_media === true
            } catch (e) {}
        }
    }
    FileView {
        id: updateFile
        path: Quickshell.env("HOME") + "/.local/state/rice/update.json"
        watchChanges: true
        blockLoading: true
        onFileChanged: reload()
        onTextChanged: {
            try { panel.updateState = JSON.parse(text()) } catch (e) {}
        }
    }

    component SectionTitle: Text {
        font.family: "Adwaita Sans"
        font.pixelSize: 11
        font.weight: Font.DemiBold
        color: "#a4a4a4"
        leftPadding: 2
    }
    component Choice: Rectangle {
        property string glyph: ""
        property string label: ""
        property bool selected: false
        signal chosen()
        height: 38
        radius: 12
        color: selected ? "#f1f1f1" : "#292929"
        border.width: selected ? 0 : 1
        border.color: "#393939"
        Row {
            anchors.centerIn: parent
            spacing: 9
            Text {
                visible: parent.parent.glyph !== ""
                text: parent.parent.glyph
                color: parent.parent.selected ? "#171717" : "#e5e5e5"
                font.family: "JetBrainsMono Nerd Font"
                font.pixelSize: 14
            }
            Text {
                text: parent.parent.label
                color: parent.parent.selected ? "#171717" : "#e5e5e5"
                font.family: "Adwaita Sans"
                font.pixelSize: 12
                font.weight: parent.parent.selected ? Font.DemiBold : Font.Normal
            }
        }
        MouseArea { anchors.fill: parent; onClicked: parent.chosen() }
    }
    component MenuRow: Rectangle {
        property string glyph: ""
        property string title: ""
        property string detail: ""
        signal chosen()
        width: parent ? parent.width : 340
        height: 48
        radius: 9
        color: pointer.containsMouse ? "#292929" : "transparent"
        Text {
            x: 10; anchors.verticalCenter: parent.verticalCenter
            text: parent.glyph
            color: "#ececec"; font.family: "JetBrainsMono Nerd Font"; font.pixelSize: 17
        }
        Column {
            x: 42; anchors.verticalCenter: parent.verticalCenter; spacing: 2
            Text { text: parent.parent.title; color: "#f1f1f1"; font.family: "Adwaita Sans"; font.pixelSize: 12; font.weight: Font.Medium }
            Text { text: parent.parent.detail; color: "#9e9e9e"; font.family: "Adwaita Sans"; font.pixelSize: 10; elide: Text.ElideRight; width: 290 }
        }
        Text { anchors.right: parent.right; anchors.rightMargin: 12; anchors.verticalCenter: parent.verticalCenter
            text: "›"; color: "#a3a3a3"; font.pixelSize: 20 }
        MouseArea { id: pointer; anchors.fill: parent; hoverEnabled: true; onClicked: parent.chosen() }
    }
    component SourceRow: Rectangle {
        property string glyph: "♫"
        property string title: ""
        property string detail: ""
        property bool enabled: false
        signal toggled(bool value)
        width: parent ? parent.width : 340
        height: 49
        radius: 9
        color: pointer.containsMouse ? "#292929" : "transparent"
        Text { x: 10; anchors.verticalCenter: parent.verticalCenter; text: parent.glyph
            color: "#e8e8e8"; font.family: "JetBrainsMono Nerd Font"; font.pixelSize: 17 }
        Column {
            x: 42; anchors.verticalCenter: parent.verticalCenter; spacing: 2
            Text { text: parent.parent.title; color: "#f1f1f1"; font.family: "Adwaita Sans"; font.pixelSize: 12 }
            Text { text: parent.parent.detail; color: "#9e9e9e"; font.family: "Adwaita Sans"; font.pixelSize: 10;
                elide: Text.ElideRight; width: 235 }
        }
        Rectangle {
            anchors.right: parent.right; anchors.rightMargin: 10; anchors.verticalCenter: parent.verticalCenter
            width: 36; height: 20; radius: 10
            color: parent.enabled ? "#efefef" : "#414141"
            Rectangle { x: parent.parent.enabled ? parent.width - width - 2 : 2; y: 2
                width: 16; height: 16; radius: 8; color: parent.parent.enabled ? "#1b1b1b" : "#c8c8c8" }
        }
        MouseArea { id: pointer; anchors.fill: parent; hoverEnabled: true; onClicked: parent.toggled(!parent.enabled) }
    }

    Rectangle {
        anchors.fill: parent
        color: "#191b1d"
        border.color: "#3a3c3e"
        border.width: 1
        radius: 15
        FocusScope {
            anchors.fill: parent
            focus: true
            Keys.onEscapePressed: panel.closeRequested()
            Column {
                anchors.fill: parent
                anchors.margins: 17
                spacing: 10
                Row {
                    width: parent.width; height: 32
                    Text { text: "Quick settings"; color: "#f2f2f2"; font.family: "Adwaita Sans";
                        font.pixelSize: 18; font.weight: Font.DemiBold; width: parent.width - 68 }
                    Text { text: "↻"; color: refreshArea.containsMouse ? "#ffffff" : "#b5b5b5"; font.pixelSize: 20;
                        width: 32; horizontalAlignment: Text.AlignHCenter
                        MouseArea { id: refreshArea; anchors.fill: parent; hoverEnabled: true;
                            onClicked: { panel.executable("rice-update-check"); profileRead.running = true; brightnessRead.running = true } } }
                    Text { text: "×"; color: closeArea.containsMouse ? "#ffffff" : "#b5b5b5"; font.pixelSize: 20;
                        width: 32; horizontalAlignment: Text.AlignHCenter
                        MouseArea { id: closeArea; anchors.fill: parent; hoverEnabled: true; onClicked: panel.closeRequested() } }
                }
                Flickable {
                    width: parent.width
                    height: parent.height - 42
                    clip: true
                    contentWidth: width
                    contentHeight: content.implicitHeight + 8
                    boundsBehavior: Flickable.StopAtBounds
                    Controls.ScrollBar.vertical: Controls.ScrollBar { policy: Controls.ScrollBar.AsNeeded }
                    Column {
                        id: content
                        width: parent.width - 6
                        spacing: 8
                        SectionTitle { visible: panel.pendingUpdate !== null; text: "UPDATE READY" }
                        MenuRow {
                            visible: panel.pendingUpdate !== null
                            glyph: ""
                            title: "Download update"
                            detail: panel.pendingUpdate ?
                                    ((panel.pendingUpdate.kind === "mandatory" ? "Mandatory · " : "") +
                                     panel.pendingUpdate.count + " new · " + panel.pendingUpdate.detail) : ""
                            onChosen: {
                                if (panel.pendingUpdate) {
                                    panel.closeRequested()
                                    panel.executable("rice-show-update", [panel.pendingUpdate.sha])
                                }
                            }
                        }
                        Choice { visible: panel.pendingUpdate !== null && panel.pendingUpdate.kind !== "mandatory";
                            width: 84; label: "Ignore"
                            onChosen: panel.executable("rice-update-ignore", [panel.pendingUpdate.sha]) }
                        SectionTitle { text: "QUICK CONTROLS" }
                        Grid {
                            width: parent.width; columns: 2; spacing: 7
                            Repeater {
                                model: [
                                    {glyph: "", name: "Sound", page: "audio"},
                                    {glyph: "", name: "Wi-Fi", page: "network"},
                                    {glyph: "", name: "Bluetooth", page: "bluetooth"},
                                    {glyph: "", name: "Media", page: "media"},
                                    {glyph: "󰍹", name: "Displays", page: "display"}
                                ]
                                Choice { width: (content.width - 7) / 2; glyph: modelData.glyph; label: modelData.name;
                                    onChosen: panel.openPage(modelData.page) }
                            }
                        }
                        Item { width: 1; height: 7 }
                        SectionTitle { text: "DISPLAY & POWER" }
                        Rectangle {
                            visible: panel.brightnessAvailable
                            width: parent.width; height: 82; radius: 10; color: "#252729"
                            Text { x: 12; y: 10; text: "☼  Brightness"; color: "#e9e9e9";
                                font.family: "Adwaita Sans"; font.pixelSize: 12 }
                            Text { anchors.right: parent.right; anchors.rightMargin: 12; y: 10;
                                text: panel.brightnessValue + "%"; color: "#c7c7c7";
                                font.family: "Adwaita Sans"; font.pixelSize: 12 }
                            Controls.Slider {
                                id: brightnessSlider
                                x: 10; y: 38; width: parent.width - 20; height: 34
                                from: 2; to: 100; value: panel.brightnessValue
                                onMoved: { panel.brightnessValue = Math.round(value); brightnessCommit.restart() }
                                background: Rectangle {
                                    x: brightnessSlider.leftPadding
                                    y: brightnessSlider.topPadding + brightnessSlider.availableHeight / 2 - height / 2
                                    width: brightnessSlider.availableWidth; height: 4; radius: 2; color: "#5a5c5d"
                                    Rectangle { width: brightnessSlider.visualPosition * parent.width; height: parent.height;
                                        radius: parent.radius; color: "#ededed" }
                                }
                                handle: Rectangle {
                                    x: brightnessSlider.leftPadding + brightnessSlider.visualPosition * (brightnessSlider.availableWidth - width)
                                    y: brightnessSlider.topPadding + brightnessSlider.availableHeight / 2 - height / 2
                                    width: 15; height: 15; radius: 8; color: "#f6f6f6"
                                }
                            }
                        }
                        Text { text: "Power mode"; color: "#a4a4a4"; font.family: "Adwaita Sans"; font.pixelSize: 11; leftPadding: 2 }
                        Row {
                            width: parent.width; spacing: 7
                            Choice { width: (parent.width - 14) / 3; label: "Saver"; selected: panel.profile === "power-saver";
                                onChosen: panel.setProfile("power-saver") }
                            Choice { width: (parent.width - 14) / 3; label: "Balanced"; selected: panel.profile === "balanced";
                                onChosen: panel.setProfile("balanced") }
                            Choice { width: (parent.width - 14) / 3; label: "Fast"; selected: panel.profile === "performance";
                                onChosen: panel.setProfile("performance") }
                        }
                        Item { width: 1; height: 7 }
                        SectionTitle { text: "MEDIA SOURCES" }
                        SourceRow { title: "Spotify app"; detail: "Show playback controls while open";
                            enabled: panel.spotifyEnabled
                            onToggled: value => { panel.spotifyEnabled = value; panel.executable(value ? "rice-spotify-on" : "rice-spotify-off") } }
                        SourceRow { title: "Browser players"; detail: "Spotify Web, SoundCloud, YouTube Music";
                            enabled: panel.browserEnabled
                            onToggled: value => { panel.browserEnabled = value; panel.executable(value ? "rice-browser-on" : "rice-browser-off") } }
                        Item { width: 1; height: 7 }
                        SectionTitle { text: "CLOCK" }
                        Row { width: parent.width; spacing: 7
                            Choice { width: (parent.width - 7) / 2; label: "24 hour"; selected: panel.clockFormat === "24h";
                                onChosen: { panel.clockFormat = "24h"; panel.executable("rice-clock-24") } }
                            Choice { width: (parent.width - 7) / 2; label: "12 hour"; selected: panel.clockFormat === "12h";
                                onChosen: { panel.clockFormat = "12h"; panel.executable("rice-clock-12") } }
                        }
                        Item { width: 1; height: 7 }
                        SectionTitle { text: "RICE" }
                        MenuRow {
                            visible: panel.pendingUpdate === null
                            glyph: "↻"
                            title: panel.updateState.error ? "Update check failed" :
                                   panel.updateState.checked ? "Rice is up to date" : "Check for updates"
                            detail: panel.updateState.error || "Check for updates"
                            onChosen: panel.executable("rice-update-check")
                        }
                        MenuRow { glyph: ""; title: "Update history"; detail: "New, old and ignored updates";
                            onChosen: panel.openPage("updates") }
                        Item { width: 1; height: 7 }
                        SectionTitle { text: "MORE" }
                        MenuRow { visible: panel.devEnabled; glyph: "󰅪"; title: "Dev Options";
                            detail: "Check errors and active machines";
                            onChosen: {
                                panel.closeRequested()
                                Quickshell.execDetached(["python3", Quickshell.env("HOME") + "/.local/share/rice/source/dev/dev-options.py"])
                            } }
                        MenuRow { glyph: "󰍛"; title: "System monitor"; detail: "CPU, memory and processes";
                            onChosen: { panel.closeRequested(); panel.executable("rice-system-monitor") } }
                        MenuRow { glyph: ""; title: "Desktop configuration"; detail: "Personalize this desktop";
                            onChosen: { panel.closeRequested(); panel.executable("rice-desktop-config") } }
                        MenuRow { glyph: "󰇮"; title: "Share an idea"; detail: "Suggest an improvement on GitHub";
                            onChosen: { panel.closeRequested(); panel.executable("rice-share-idea") } }
                    }
                }
            }
        }
    }
}
