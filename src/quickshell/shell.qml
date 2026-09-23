import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Hyprland

ShellRoot {
    id: root
    // One property per bar-status field: the --watch stream only re-evaluates
    // bindings whose value actually changed (defaults fill within ~0.4s).
    property string audio: ""
    property string audio_tooltip: ""
    property string network: ""
    property string network_tooltip: ""
    property string display: ""
    property string display_tooltip: ""
    property string bluetooth: ""
    property string spotify: ""
    property bool spotify_running: false
    property string cover: ""
    property string track: ""
    property string repeat: ""
    property string repeat_tooltip: ""
    property string shuffle: ""
    property string shuffle_tooltip: ""
    property string battery: ""
    property var palette: ({background: "#161616", foreground: "#e4e4e4", border: "#3b3b3b", muted: "#a3a3a3", accent: "#dedede", accent_foreground: "#181818", hover: "#303030"})
    property string timeFormat: "24h"
    property string kickPath: Quickshell.env("HOME") + "/.local/state/rice/status-kick"

    function applyState(line) {
        if (!line || line.charAt(0) !== "{") return
        var s
        try { s = JSON.parse(line) } catch (e) { console.warn("status JSON: " + e); return }
        if (typeof s.audio === "string" && s.audio !== audio) audio = s.audio
        if (typeof s.audio_tooltip === "string" && s.audio_tooltip !== audio_tooltip) audio_tooltip = s.audio_tooltip
        if (typeof s.network === "string" && s.network !== network) network = s.network
        if (typeof s.network_tooltip === "string" && s.network_tooltip !== network_tooltip) network_tooltip = s.network_tooltip
        if (typeof s.display === "string" && s.display !== display) display = s.display
        if (typeof s.display_tooltip === "string" && s.display_tooltip !== display_tooltip) display_tooltip = s.display_tooltip
        if (typeof s.bluetooth === "string" && s.bluetooth !== bluetooth) bluetooth = s.bluetooth
        if (typeof s.spotify === "string" && s.spotify !== spotify) spotify = s.spotify
        if (typeof s.spotify_running === "boolean" && s.spotify_running !== spotify_running) spotify_running = s.spotify_running
        if (typeof s.cover === "string" && s.cover !== cover) cover = s.cover
        if (typeof s.track === "string" && s.track !== track) track = s.track
        if (typeof s.repeat === "string" && s.repeat !== repeat) repeat = s.repeat
        if (typeof s.repeat_tooltip === "string" && s.repeat_tooltip !== repeat_tooltip) repeat_tooltip = s.repeat_tooltip
        if (typeof s.shuffle === "string" && s.shuffle !== shuffle) shuffle = s.shuffle
        if (typeof s.shuffle_tooltip === "string" && s.shuffle_tooltip !== shuffle_tooltip) shuffle_tooltip = s.shuffle_tooltip
        if (typeof s.battery === "string" && s.battery !== battery) battery = s.battery
    }
    function action(args) {
        Quickshell.execDetached(args)
        Quickshell.execDetached(["touch", kickPath])   // watcher re-reads within ~100ms
    }

    FileView {
        id: colors
        path: Quickshell.env("HOME") + "/.local/state/rice/palette.json"
        watchChanges: true
        blockLoading: true
        onFileChanged: reload()
        onTextChanged: {
            try { root.palette = JSON.parse(text()) } catch (e) {}
        }
        Component.onCompleted: {
            try { root.palette = JSON.parse(text()) } catch (e) {}
        }
    }
    FileView {
        id: settings
        path: Quickshell.env("HOME") + "/.config/rice/settings.json"
        watchChanges: true
        blockLoading: true
        onFileChanged: reload()
        onTextChanged: {
            try { root.timeFormat = JSON.parse(text()).time_format === "12h" ? "12h" : "24h" } catch (e) {}
        }
        Component.onCompleted: {
            try { root.timeFormat = JSON.parse(text()).time_format === "12h" ? "12h" : "24h" } catch (e) {}
        }
    }
    Process {
        id: statusStream
        command: [Quickshell.env("HOME") + "/.local/bin/bar-status", "--watch"]
        running: true
        stdout: SplitParser {
            onRead: data => root.applyState(data)
        }
        stderr: SplitParser {
            onRead: data => console.warn("bar-status: " + data)
        }
        onExited: statusRestart.restart()
    }
    Timer { id: statusRestart; interval: 1000; onTriggered: statusStream.running = true }
    SystemClock { id: clock; precision: SystemClock.Seconds }

    Variants {
        model: Quickshell.screens
        PanelWindow {
            id: panel
            property var modelData
            screen: modelData
            anchors { top: true; left: true; right: true }
            implicitHeight: 40
            color: "transparent"
            exclusiveZone: 40

            Rectangle {
                id: leftGroup
                anchors.left: parent.left
                anchors.leftMargin: 8
                anchors.verticalCenter: parent.verticalCenter
                implicitWidth: leftRow.implicitWidth + (root.timeFormat === "12h" ? 16 : 12)
                height: 31
                radius: 10
                color: root.palette.background
                Behavior on color { ColorAnimation { duration: 200 } }
                border.width: 1
                border.color: root.palette.border
                Row {
                    id: leftRow
                    objectName: "riceLeftRow"
                    anchors.centerIn: parent
                    spacing: 0
                    BarButton { label: "  " + Qt.formatDateTime(clock.date, root.timeFormat === "12h" ? "hh:mm:ss AP" : "hh:mm:ss"); id: clockBtn; minimumWidth: clockMax.implicitWidth + 16; hint: Qt.formatDateTime(clock.date, "dddd, dd MMMM yyyy"); ink: root.palette.foreground; hoverColor: root.palette.hover; pal: root.palette }
                    Text {
                        id: clockMax
                        visible: false
                        font.family: "Adwaita Sans"
                        font.pixelSize: 12
                        text: clockBtn.label.replace(/[0-9]/g, "8")
                    }
                    BarButton {
                        label: root.audio; hint: root.audio_tooltip || ""; ink: root.palette.foreground; hoverColor: root.palette.hover; pal: root.palette
                        onClicked: button => root.action(button === Qt.RightButton ? [Quickshell.env("HOME") + "/.local/bin/desktop-menu", "audio"] : [Quickshell.env("HOME") + "/.local/bin/desktop-menu", "audio", button === Qt.MiddleButton ? "boost" : "mute"])
                        onWheeled: delta => root.action([Quickshell.env("HOME") + "/.local/bin/desktop-menu", "audio", delta > 0 ? "up" : "down"])
                    }
                    Item {
                        id: albumCover
                        visible: root.spotify_running && root.cover !== ""
                        width: 24; height: 24
                        Image { anchors.fill: parent; source: root.cover !== "" ? "file://" + root.cover : ""; asynchronous: true; fillMode: Image.PreserveAspectFit; sourceSize.width: 24; sourceSize.height: 24 }
                        MouseArea {
                            id: albumPointer
                            anchors.fill: parent; hoverEnabled: true
                            onClicked: root.action([Quickshell.env("HOME") + "/.local/bin/desktop-panel", "media"])
                            onContainsMouseChanged: {
                                if (containsMouse)
                                    albumDelay.restart()
                                else {
                                    albumDelay.stop()
                                    albumCover.albumTipShown = false
                                }
                            }
                        }
                        property bool albumTipShown: false
                        Timer {
                            id: albumDelay
                            interval: 300                 // matches waybar-tooltip.lua delay_ms
                            onTriggered: albumCover.albumTipShown = true
                        }
                        // Own surface: the 40px panel clipped the old ToolTip.
                        PopupWindow {
                            id: albumTip
                            anchor.item: albumCover
                            anchor.rect.x: (albumCover.width - width) / 2
                            anchor.rect.y: albumCover.height + 7
                            implicitWidth: albumTipRect.implicitWidth
                            implicitHeight: albumTipRect.implicitHeight
                            color: "transparent"
                            visible: albumCover.albumTipShown && root.track !== ""
                            Rectangle {
                                id: albumTipRect
                                anchors.fill: parent
                                implicitWidth: albumTipText.implicitWidth + 16
                                implicitHeight: albumTipText.implicitHeight + 12
                                color: root.palette.background
                                Behavior on color { ColorAnimation { duration: 200 } }
                                border.width: 1
                                border.color: root.palette.border
                                radius: 6
                                Text {
                                    id: albumTipText
                                    anchors.centerIn: parent
                                    text: root.track
                                    color: root.palette.foreground
                                    font.family: "Adwaita Sans"
                                    font.pixelSize: 12
                                    textFormat: Text.PlainText
                                }
                            }
                        }
                    }
                    BarButton { visible: root.spotify_running && root.shuffle !== ""; glyphSize: 16; label: root.shuffle; hint: root.shuffle_tooltip || ""; ink: root.palette.foreground; hoverColor: root.palette.hover; pal: root.palette; onClicked: button => root.action(button === Qt.RightButton ? [Quickshell.env("HOME") + "/.local/bin/desktop-panel", "media"] : [Quickshell.env("HOME") + "/.local/bin/waybar-spotify", "--toggle-shuffle"]) }
                    BarButton { visible: root.spotify_running; glyphSize: 24; label: "󰒮"; hint: "Previous track"; ink: root.palette.foreground; hoverColor: root.palette.hover; pal: root.palette; onClicked: root.action([Quickshell.env("HOME") + "/.local/bin/rice-media", "previous"]) }
                    BarButton { visible: root.spotify_running; glyphSize: 24; label: root.spotify; hint: "Play / pause"; ink: root.palette.foreground; hoverColor: root.palette.hover; pal: root.palette; onClicked: button => root.action(button === Qt.RightButton ? [Quickshell.env("HOME") + "/.local/bin/desktop-panel", "media"] : [Quickshell.env("HOME") + "/.local/bin/rice-media", "toggle"]); onWheeled: delta => root.action([Quickshell.env("HOME") + "/.local/bin/rice-media", delta > 0 ? "up" : "down"]) }
                    BarButton { visible: root.spotify_running; glyphSize: 24; label: "󰒭"; hint: "Next track"; ink: root.palette.foreground; hoverColor: root.palette.hover; pal: root.palette; onClicked: root.action([Quickshell.env("HOME") + "/.local/bin/rice-media", "next"]) }
                    BarButton { visible: root.spotify_running && root.repeat !== ""; glyphSize: 16; label: root.repeat; hint: root.repeat_tooltip || ""; ink: root.palette.foreground; hoverColor: root.palette.hover; pal: root.palette; onClicked: root.action([Quickshell.env("HOME") + "/.local/bin/waybar-spotify", "--cycle-repeat"]) }
                }
            }
            Rectangle {
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.verticalCenter: parent.verticalCenter
                implicitWidth: workspaces.implicitWidth + 12
                height: 31
                radius: 10
                color: root.palette.background
                Behavior on color { ColorAnimation { duration: 200 } }
                border.width: 1
                border.color: root.palette.border
                Row {
                    id: workspaces
                    anchors.centerIn: parent
                    spacing: 2
                    Repeater {
                        model: 5
                        BarButton {
                            required property int index
                            label: String(index + 1)
                            minimumWidth: 39
                            implicitHeight: 22
                            radius: 5
                            active: Hyprland.focusedWorkspace && Hyprland.focusedWorkspace.id === index + 1
                            ink: active ? root.palette.accent_foreground : root.palette.muted
                            activeColor: root.palette.accent
                            hoverColor: root.palette.hover; pal: root.palette
                            // Hyprland ≥0.56 evaluates dispatchers as Lua:
                            // "hl.dsp.focus" is the working form here (plain
                            // "workspace N" errors with a parse exception).
                            onClicked: Hyprland.dispatch("hl.dsp.focus({workspace=" + (index + 1) + "})")
                        }
                    }
                }
            }
            Rectangle {
                anchors.right: parent.right
                anchors.rightMargin: 8
                anchors.verticalCenter: parent.verticalCenter
                implicitWidth: rightRow.implicitWidth
                height: 31
                radius: 10
                color: root.palette.background
                Behavior on color { ColorAnimation { duration: 200 } }
                border.width: 1
                border.color: root.palette.border
                Row {
                    id: rightRow
                    anchors.centerIn: parent
                    BarButton { label: "󰨞"; hint: "VS Code · middle click: folder · right click: focus"; ink: root.palette.foreground; hoverColor: root.palette.hover; pal: root.palette; onClicked: button => root.action(button === Qt.MiddleButton ? [Quickshell.env("HOME") + "/.local/bin/vscode-menu", "folder"] : button === Qt.RightButton ? [Quickshell.env("HOME") + "/.local/bin/vscode-menu", "focus"] : [Quickshell.env("HOME") + "/.local/bin/vscode-menu"]) }
                    BarButton { label: ""; hint: "Terminal"; ink: root.palette.foreground; hoverColor: root.palette.hover; pal: root.palette; onClicked: root.action(["kitty"]) }
                    BarButton { label: ""; hint: "Files"; ink: root.palette.foreground; hoverColor: root.palette.hover; pal: root.palette; onClicked: root.action(["thunar"]) }
                    BarButton { visible: root.display !== ""; label: root.display; hint: root.display_tooltip || "Displays"; ink: root.palette.foreground; hoverColor: root.palette.hover; pal: root.palette; onClicked: root.action([Quickshell.env("HOME") + "/.local/bin/desktop-panel", "display"]) }
                    BarButton { visible: root.bluetooth !== ""; label: root.bluetooth; hint: "Bluetooth devices"; ink: root.palette.foreground; hoverColor: root.palette.hover; pal: root.palette; onClicked: root.action([Quickshell.env("HOME") + "/.local/bin/desktop-menu", "bluetooth"]) }
                    BarButton { label: root.network; hint: root.network_tooltip || "Networks"; ink: root.palette.foreground; hoverColor: root.palette.hover; pal: root.palette; onClicked: root.action([Quickshell.env("HOME") + "/.local/bin/desktop-menu", "network"]) }
                    BarButton { visible: root.battery !== ""; label: "  " + root.battery; hint: "Battery · " + root.battery; ink: root.palette.foreground; hoverColor: root.palette.hover; pal: root.palette }
                    BarButton { label: ""; hint: "Quick settings"; ink: root.palette.foreground; hoverColor: root.palette.hover; pal: root.palette; onClicked: root.action([Quickshell.env("HOME") + "/.local/bin/control-menu"]) }
                    BarButton { label: ""; hint: "Power / session · triple click: shut down"; ink: root.palette.foreground; hoverColor: root.palette.hover; pal: root.palette; onClicked: root.action([Quickshell.env("HOME") + "/.local/bin/power-click"]) }
                }
            }
        }
    }
}
