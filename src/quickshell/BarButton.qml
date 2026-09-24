import QtQuick
import Quickshell

Rectangle {
    id: button
    property string label: ""
    property string hint: ""
    property string clickInfo: ""
    property string wheelInfo: ""
    property string shownInfo: ""
    property string tipAlign: parent && parent.objectName === "riceRightRow" ? "right" : parent && parent.objectName === "riceLeftRow" ? "left" : "center"
    property color ink: "#e4e4e4"
    property color hoverColor: "#303030"
    property color activeColor: "#dedede"
    property var pal: null          // palette for the tooltip surface
    property bool active: false
    property bool attention: false
    property bool interactive: true
    property int minimumWidth: 0
    property int glyphSize: 12       // media transport glyphs opt into 24
    property int horizontalPadding: parent && parent.objectName === "riceLeftRow" ? 7 : 6
    property bool tipShown: false
    signal clicked(int button)
    signal wheeled(int delta)
    implicitWidth: Math.max(minimumWidth, text.implicitWidth + 2 * horizontalPadding)
    implicitHeight: 26
    radius: 6
    color: interactive && pointer.pressed ? "#505050" : active ? activeColor : interactive && pointer.containsMouse ? hoverColor : "transparent"
    border.width: attention && !active ? 1 : 0
    border.color: activeColor
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
        acceptedButtons: button.interactive ? Qt.LeftButton | Qt.RightButton | Qt.MiddleButton : Qt.NoButton
        onClicked: mouse => {
            button.shownInfo = button.clickInfo || "Action requested"
            button.tipShown = true
            actionDelay.restart()
            button.clicked(mouse.button)
        }
        onWheel: wheel => {
            if (button.interactive) {
                button.shownInfo = button.wheelInfo || "Adjustment requested"
                button.tipShown = true
                actionDelay.restart()
                button.wheeled(wheel.angleDelta.y)
            }
            else wheel.accepted = false
        }
        onContainsMouseChanged: {
            if (containsMouse)
                tipDelay.restart()
            else {
                tipDelay.stop()
                button.tipShown = false
                actionDelay.stop()
                button.shownInfo = ""
            }
        }
    }
    Timer {
        id: tipDelay
        interval: 300
        onTriggered: button.tipShown = true
    }
    Timer {
        id: actionDelay
        interval: 1300
        onTriggered: button.shownInfo = ""
    }
    // Renders hint below the bar on its own surface, so the 40px panel
    // cannot clip it (QtQuick.Controls ToolTip never escaped the window).
    PopupWindow {
        anchor.item: button
        anchor.rect.x: button.tipAlign === "right" ? button.width - width : button.tipAlign === "left" ? 0 : (button.width - width) / 2
        anchor.rect.y: button.height + 7
        implicitWidth: tipRect.implicitWidth
        implicitHeight: tipRect.implicitHeight
        color: "transparent"
        visible: button.tipShown && (button.shownInfo !== "" || button.hint !== "")
        Rectangle {
            id: tipRect
            anchors.fill: parent
            implicitWidth: Math.min(tipMeasure.implicitWidth + 16, 356)
            implicitHeight: tipText.implicitHeight + 12
            color: button.pal ? button.pal.background : "#161616"
            border.width: 1
            border.color: button.pal ? button.pal.border : "#3b3b3b"
            radius: 6
            Text {
                id: tipMeasure
                visible: false
                text: button.shownInfo || button.hint
                font.family: "Adwaita Sans"
                font.pixelSize: 12
            }
            Text {
                id: tipText
                anchors.centerIn: parent
                width: parent.width - 16
                text: button.shownInfo || button.hint
                color: button.ink
                font.family: "Adwaita Sans"
                font.pixelSize: 12
                wrapMode: Text.WordWrap
                textFormat: Text.PlainText
            }
        }
    }
}
