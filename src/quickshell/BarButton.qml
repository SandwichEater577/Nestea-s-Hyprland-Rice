import QtQuick
import Quickshell

Rectangle {
    id: button
    property string label: ""
    property string hint: ""
    property color ink: "#e4e4e4"
    property color hoverColor: "#303030"
    property color activeColor: "#dedede"
    property var pal: null          // palette for the tooltip surface
    property bool active: false
    property int minimumWidth: 0
    property int glyphSize: 12       // media transport glyphs opt into 24
    property int horizontalPadding: parent && parent.objectName === "riceLeftRow" ? 7 : 6
    property bool tipShown: false
    signal clicked(int button)
    signal wheeled(int delta)
    implicitWidth: Math.max(minimumWidth, text.implicitWidth + 2 * horizontalPadding)
    implicitHeight: 26
    radius: 6
    color: active ? activeColor : pointer.containsMouse ? hoverColor : "transparent"
    Behavior on color { ColorAnimation { duration: 200 } }
    Text {
        id: text
        anchors.centerIn: parent
        text: button.label
        color: button.ink
        Behavior on color { ColorAnimation { duration: 200 } }
        font.family: "Adwaita Sans"
        font.pixelSize: button.glyphSize
    }
    MouseArea {
        id: pointer
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.LeftButton | Qt.RightButton | Qt.MiddleButton
        onClicked: mouse => button.clicked(mouse.button)
        onWheel: wheel => button.wheeled(wheel.angleDelta.y)
        onContainsMouseChanged: {
            if (containsMouse)
                tipDelay.restart()
            else {
                tipDelay.stop()
                button.tipShown = false
            }
        }
    }
    Timer {
        id: tipDelay
        interval: 300                 // matches waybar-tooltip.lua delay_ms
        onTriggered: button.tipShown = true
    }
    // Renders hint below the bar on its own surface, so the 40px panel
    // cannot clip it (QtQuick.Controls ToolTip never escaped the window).
    PopupWindow {
        anchor.item: button
        anchor.rect.x: (button.width - width) / 2
        anchor.rect.y: button.height + 7
        implicitWidth: tipRect.implicitWidth
        implicitHeight: tipRect.implicitHeight
        color: "transparent"
        visible: button.tipShown && button.hint !== ""
        Rectangle {
            id: tipRect
            anchors.fill: parent
            implicitWidth: tipText.implicitWidth + 16
            implicitHeight: tipText.implicitHeight + 12
            color: button.pal ? button.pal.background : "#161616"
            border.width: 1
            border.color: button.pal ? button.pal.border : "#3b3b3b"
            radius: 6
            Text {
                id: tipText
                anchors.centerIn: parent
                text: button.hint
                color: button.ink
                font.family: "Adwaita Sans"
                font.pixelSize: 12
                textFormat: Text.PlainText
            }
        }
    }
}
