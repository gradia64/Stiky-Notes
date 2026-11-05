import QtQuick

// Piccolo pulsante piatto per la barra della nota e la barra di formattazione
Rectangle {
    id: button

    property string glyph
    property string tip
    property bool checked: false
    property alias font: label.font
    signal clicked()

    width: 24
    height: 24
    radius: 4
    color: mouse.containsMouse || checked
           ? Qt.rgba(0, 0, 0, mouse.pressed ? 0.18 : (checked ? 0.14 : 0.09))
           : "transparent"

    Text {
        id: label
        anchors.centerIn: parent
        text: button.glyph
        color: "#262626"
        font.pixelSize: 15
    }

    MouseArea {
        id: mouse
        anchors.fill: parent
        hoverEnabled: true
        onClicked: button.clicked()
    }

    // Accessibilità: nome leggibile dagli screen reader
    Accessible.role: Accessible.Button
    Accessible.name: button.tip
}
