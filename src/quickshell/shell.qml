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
    property string battery_icon: ""
    property string battery_tooltip: ""
    property var palette: ({background: "#161616", foreground: "#e4e4e4", border: "#3b3b3b", muted: "#a3a3a3", accent: "#dedede", accent_foreground: "#181818", hover: "#303030"})
    property string timeFormat: "24h"
    property string kickPath: Quickshell.env("HOME") + "/.local/state/rice/status-kick"
    property int activeWorkspace: 0
    property var visibleWorkspaces: [1, 2, 3, 4, 5]
    property var workspaceAttention: []
    property bool nativeReady: false
    property bool managerReady: false
    property int spotifyManageButtonSize: 24
    property bool hasCode: false
    property bool hasKitty: false
    property bool hasThunar: false
    property bool hasBtop: false
    property bool settingsOpen: false
    property var settingsScreen: Quickshell.screens[0]
    IpcHandler {
        target: "settings"
        function toggle(): void { root.settingsOpen = !root.settingsOpen }
        function open(): void { root.settingsOpen = true }
        function close(): void { root.settingsOpen = false }
    }

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
        if (typeof s.battery_icon === "string" && s.battery_icon !== battery_icon) battery_icon = s.battery_icon
        if (typeof s.battery_tooltip === "string" && s.battery_tooltip !== battery_tooltip) battery_tooltip = s.battery_tooltip
    }
    function action(args) {
        Quickshell.execDetached(args)
        Quickshell.execDetached(["touch", kickPath])   // watcher re-reads within ~100ms
    }
    function runNative(name, fallback) {
        if (nativeReady) Quickshell.execDetached([name])
        else action(fallback)
    }
    function runManaged(actionName, nativeName, fallback) {
        if (managerReady) Quickshell.execDetached(["waybar-manager.exec", actionName])
        else runNative(nativeName, fallback)
    }
    Process {
        command: ["sh", "-c", "command -v rice-actions >/dev/null && command -v rice-show-settings >/dev/null && command -v rice-terminal >/dev/null"]
        running: true
        onExited: (code) => root.nativeReady = code === 0
    }
    Process { command: ["sh", "-c", "command -v waybar-manager.exec >/dev/null"]; running: true
        onExited: (code) => root.managerReady = code === 0 }
    Process { command: ["sh", "-c", "command -v code >/dev/null"]; running: true
        onExited: (code) => root.hasCode = code === 0 }
    Process { command: ["sh", "-c", "command -v kitty >/dev/null"]; running: true
        onExited: (code) => root.hasKitty = code === 0 }
    Process { command: ["sh", "-c", "command -v thunar >/dev/null"]; running: true
        onExited: (code) => root.hasThunar = code === 0 }
    Process { command: ["sh", "-c", "command -v btop >/dev/null"]; running: true
        onExited: (code) => root.hasBtop = code === 0 }

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
    FileView {
        path: Quickshell.env("HOME") + "/.config/rice/bar-controls.json"
        watchChanges: true
        blockLoading: true
        onFileChanged: reload()
        onTextChanged: {
            try {
                var size = Number(JSON.parse(text()).spotify_manage_button_size)
                if (size >= 16 && size <= 26) root.spotifyManageButtonSize = size
            } catch (e) {}
        }
    }
    Process {
        id: statusStream
        command: ["sh", "-c", "if command -v rice-status >/dev/null; then exec rice-status --watch; else exec bar-status --watch; fi"]
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
    Process {
        id: workspaceStream
        command: ["rice-workspace", "--stream"]
        running: true
        stdout: SplitParser {
            onRead: data => {
                try {
                    var s = JSON.parse(data)
                    root.activeWorkspace = s.active || 0
                    root.visibleWorkspaces = s.visible || [1, 2, 3, 4, 5]
                    root.workspaceAttention = s.attention || []
                } catch (e) { console.warn("workspace JSON: " + e) }
            }
        }
        onExited: workspaceRestart.restart()
    }
    Timer { id: workspaceRestart; interval: 1000; onTriggered: workspaceStream.running = true }
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
                    BarButton { label: "  " + Qt.formatDateTime(clock.date, root.timeFormat === "12h" ? "hh:mm:ss AP" : "hh:mm:ss"); id: clockBtn; interactive: false; minimumWidth: clockMax.implicitWidth + 16; hint: Qt.formatDateTime(clock.date, "dddd, dd MMMM yyyy"); ink: root.palette.foreground; hoverColor: root.palette.hover; pal: root.palette }
                    Text {
                        id: clockMax
                        visible: false
                        font.family: "Adwaita Sans"
                        font.pixelSize: 12
                        text: clockBtn.label.replace(/[0-9]/g, "8")
                    }
                    BarButton {
                        label: root.audio; hint: (root.audio_tooltip || "Audio") + " · left: mute · middle: boost · right: outputs · wheel: volume"; clickInfo: "Audio control sent"; wheelInfo: "Changing volume"; ink: root.palette.foreground; hoverColor: root.palette.hover; pal: root.palette
                        onClicked: button => root.runManaged(button === Qt.RightButton ? "audio-open-button" : button === Qt.MiddleButton ? "audio-boost-button" : "audio-mute-button", button === Qt.RightButton ? "rice-show-audio" : button === Qt.MiddleButton ? "rice-audio-boost" : "rice-audio-mute", button === Qt.RightButton ? ["desktop-menu", "audio"] : ["desktop-menu", "audio", button === Qt.MiddleButton ? "boost" : "mute"])
                        onWheeled: delta => root.runManaged(delta > 0 ? "audio-volume-up" : "audio-volume-down", delta > 0 ? "rice-audio-up" : "rice-audio-down", ["desktop-menu", "audio", delta > 0 ? "up" : "down"])
                    }
                    Item {
                        id: albumCover
                        visible: root.spotify_running && root.cover !== ""
                        width: 24; height: 24
                        Image { anchors.fill: parent; source: root.cover !== "" ? (root.cover.indexOf("://") !== -1 ? root.cover : "file://" + root.cover) : ""; asynchronous: true; fillMode: Image.PreserveAspectFit; sourceSize.width: 24; sourceSize.height: 24 }
                        Rectangle { anchors.fill: parent; color: "#ffffff"; opacity: albumPointer.pressed ? 0.25 : 0 }
                        MouseArea {
                            id: albumPointer
                            anchors.fill: parent; hoverEnabled: true
                            onClicked: {
                                albumCover.albumActionInfo = "Opening Media"
                                albumCover.albumTipShown = true
                                albumActionDelay.restart()
                                root.runManaged("spotify-open-button", "rice-show-media", ["desktop-panel", "media"])
                            }
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
                        property string albumActionInfo: ""
                        Timer { id: albumActionDelay; interval: 1300; onTriggered: albumCover.albumActionInfo = "" }
                        Timer {
                            id: albumDelay
                            interval: 300
                            onTriggered: albumCover.albumTipShown = true
                        }
                        // Own surface: the 40px panel clipped the old ToolTip.
                        PopupWindow {
                            id: albumTip
                            anchor.item: albumCover
                            anchor.rect.x: 0
                            anchor.rect.y: albumCover.height + 7
                            implicitWidth: albumTipRect.implicitWidth
                            implicitHeight: albumTipRect.implicitHeight
                            color: "transparent"
                            visible: albumCover.albumTipShown
                            Rectangle {
                                id: albumTipRect
                                anchors.fill: parent
                                implicitWidth: Math.min(albumTipMeasure.implicitWidth + 16, 356)
                                implicitHeight: albumTipText.implicitHeight + 12
                                color: root.palette.background
                                Behavior on color { ColorAnimation { duration: 200 } }
                                border.width: 1
                                border.color: root.palette.border
                                radius: 6
                                Text {
                                    id: albumTipMeasure
                                    visible: false
                                    text: albumCover.albumActionInfo || (root.track ? root.track + " · click to open Media" : "Open Media")
                                    font.family: "Adwaita Sans"
                                    font.pixelSize: 12
                                }
                                Text {
                                    id: albumTipText
                                    anchors.centerIn: parent
                                    width: parent.width - 16
                                    text: albumCover.albumActionInfo || (root.track ? root.track + " · click to open Media" : "Open Media")
                                    color: root.palette.foreground
                                    font.family: "Adwaita Sans"
                                    font.pixelSize: 12
                                    wrapMode: Text.WordWrap
                                    textFormat: Text.PlainText
                                }
                            }
                        }
                    }
                    BarButton { visible: root.spotify_running && root.shuffle !== ""; glyphSize: 16; label: root.shuffle; hint: (root.shuffle_tooltip || "Shuffle") + " · click: toggle · right: Media"; clickInfo: "Shuffle action sent"; ink: root.palette.foreground; hoverColor: root.palette.hover; pal: root.palette; onClicked: button => root.runManaged(button === Qt.RightButton ? "spotify-open-button" : "spotify-shuffle-button", button === Qt.RightButton ? "rice-show-media" : "rice-media-shuffle", button === Qt.RightButton ? ["desktop-panel", "media"] : ["rice-media", "shuffle"]) }
                    BarButton { visible: root.spotify_running; glyphSize: root.spotifyManageButtonSize; label: "󰒮"; hint: "Play previous track"; clickInfo: "Previous track requested"; ink: root.palette.foreground; hoverColor: root.palette.hover; pal: root.palette; onClicked: root.runManaged("spotify-previous-button", "rice-media-previous", ["rice-media", "previous"]) }
                    BarButton { visible: root.spotify_running; glyphSize: root.spotifyManageButtonSize; label: root.spotify; hint: "Click: play or pause · right: Media · wheel: volume"; clickInfo: "Playback action sent"; wheelInfo: "Changing media volume"; ink: root.palette.foreground; hoverColor: root.palette.hover; pal: root.palette; onClicked: button => root.runManaged(button === Qt.RightButton ? "spotify-open-button" : "spotify-play-button", button === Qt.RightButton ? "rice-show-media" : "rice-media-toggle", button === Qt.RightButton ? ["desktop-panel", "media"] : ["rice-media", "toggle"]); onWheeled: delta => root.runManaged(delta > 0 ? "spotify-volume-up" : "spotify-volume-down", delta > 0 ? "rice-media-up" : "rice-media-down", ["rice-media", delta > 0 ? "up" : "down"]) }
                    BarButton { visible: root.spotify_running; glyphSize: root.spotifyManageButtonSize; label: "󰒭"; hint: "Play next track"; clickInfo: "Next track requested"; ink: root.palette.foreground; hoverColor: root.palette.hover; pal: root.palette; onClicked: root.runManaged("spotify-next-button", "rice-media-next", ["rice-media", "next"]) }
                    BarButton { visible: root.spotify_running && root.repeat !== ""; glyphSize: 16; label: root.repeat; hint: (root.repeat_tooltip || "Repeat") + " · click: cycle mode"; clickInfo: "Repeat mode change requested"; ink: root.palette.foreground; hoverColor: root.palette.hover; pal: root.palette; onClicked: root.runManaged("spotify-repeat-button", "rice-media-repeat", ["rice-media", "repeat"]) }
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
                        model: root.visibleWorkspaces
                        BarButton {
                            required property int modelData
                            label: String(modelData)
                            hint: "Switch to workspace " + modelData
                            clickInfo: "Switching to workspace " + modelData
                            minimumWidth: 39
                            implicitHeight: 22
                            radius: 5
                            active: root.activeWorkspace === modelData
                            attention: root.workspaceAttention.indexOf(modelData) !== -1
                            ink: active ? root.palette.accent_foreground : attention ? root.palette.accent : root.palette.muted
                            activeColor: root.palette.accent
                            hoverColor: root.palette.hover; pal: root.palette
                            // The native handler uses Hyprland's Lua dispatcher.
                            onClicked: {
                                if (root.managerReady)
                                    Quickshell.execDetached(["waybar-manager.exec", "workspace-focus-button", String(modelData)])
                                else if (root.nativeReady)
                                    Quickshell.execDetached(["rice-workspace-focus", String(modelData)])
                                else Hyprland.dispatch("hl.dsp.focus({workspace=" + modelData + "})")
                            }
                        }
                    }
                }
            }
            Rectangle {
                anchors.right: parent.right
                anchors.rightMargin: 8
                anchors.verticalCenter: parent.verticalCenter
                implicitWidth: rightRow.implicitWidth + 4 // 2 px on each horizontal side
                height: 31
                radius: 10
                color: root.palette.background
                Behavior on color { ColorAnimation { duration: 200 } }
                border.width: 1
                border.color: root.palette.border
                Row {
                    id: rightRow
                    objectName: "riceRightRow"
                    anchors.centerIn: parent
                    BarButton { visible: root.hasCode; label: "󰨞"; hint: "VS Code · click: projects · middle: folder · right: focus"; clickInfo: "VS Code action requested"; ink: root.palette.foreground; hoverColor: root.palette.hover; pal: root.palette; onClicked: button => root.runManaged(button === Qt.MiddleButton ? "vscode-folder-button" : button === Qt.RightButton ? "vscode-focus-button" : "vscode-project-button", button === Qt.MiddleButton ? "rice-vscode-folder" : button === Qt.RightButton ? "rice-vscode-focus" : "rice-vscode-menu", button === Qt.MiddleButton ? ["vscode-menu", "folder"] : button === Qt.RightButton ? ["vscode-menu", "focus"] : ["vscode-menu"]) }
                    BarButton { visible: root.hasKitty; label: ""; hint: "Open terminal"; clickInfo: "Opening terminal"; ink: root.palette.foreground; hoverColor: root.palette.hover; pal: root.palette; onClicked: root.runManaged("terminal-open-button", "rice-terminal", ["kitty"]) }
                    BarButton { visible: root.hasThunar; label: ""; hint: "Open files"; clickInfo: "Opening files"; ink: root.palette.foreground; hoverColor: root.palette.hover; pal: root.palette; onClicked: root.runManaged("files-open-button", "rice-files", ["thunar"]) }
                    BarButton { visible: root.display !== ""; label: root.display; hint: (root.display_tooltip || "Displays") + " · click: display controls"; clickInfo: "Opening display controls"; ink: root.palette.foreground; hoverColor: root.palette.hover; pal: root.palette; onClicked: root.runManaged("display-open-button", "rice-show-display", ["desktop-panel", "display"]) }
                    BarButton { visible: root.bluetooth !== ""; label: root.bluetooth; hint: "Open Bluetooth devices"; clickInfo: "Opening Bluetooth controls"; ink: root.palette.foreground; hoverColor: root.palette.hover; pal: root.palette; onClicked: root.runManaged("bluetooth-open-button", "rice-show-bluetooth", ["desktop-menu", "bluetooth"]) }
                    BarButton { label: root.network; hint: (root.network_tooltip || "Networks") + " · click: network controls"; clickInfo: "Opening network controls"; ink: root.palette.foreground; hoverColor: root.palette.hover; pal: root.palette; onClicked: root.runManaged("network-open-button", "rice-show-network", ["desktop-menu", "network"]) }
                    BarButton { visible: root.battery !== ""; interactive: false; label: root.battery_icon + "  " + root.battery; hint: root.battery_tooltip || "Battery status"; ink: root.palette.foreground; hoverColor: root.palette.hover; pal: root.palette }
                    BarButton { id: settingsButton; label: ""; hint: "Open Quick settings"; clickInfo: "Quick settings toggled"; ink: root.palette.foreground; hoverColor: root.palette.hover; pal: root.palette; onClicked: {
                        root.settingsScreen = panel.screen
                        root.settingsOpen = !root.settingsOpen
                    } }
                    BarButton { label: ""; hint: "Session menu · triple click: shut down"; clickInfo: "Power action requested"; ink: root.palette.foreground; hoverColor: root.palette.hover; pal: root.palette; onClicked: root.managerReady ? Quickshell.execDetached(["waybar-manager.exec", "power-open-button"]) : root.action(["power-click"]) }
                }
            }
            SettingsPanel {
                trigger: settingsButton
                shown: root.settingsOpen && root.settingsScreen === panel.screen
                nativeReady: root.nativeReady
                managerReady: root.managerReady
                hasCode: root.hasCode
                hasKitty: root.hasKitty
                hasBtop: root.hasBtop
                hasBattery: root.battery !== ""
                onCloseRequested: root.settingsOpen = false
            }
        }
    }
}
