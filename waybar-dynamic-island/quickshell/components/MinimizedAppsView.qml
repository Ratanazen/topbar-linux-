import QtQuick
import "../services"
import "../themes"

FocusScope {
    id: root
    width: parent.width
    implicitHeight: Math.min(260, contentCol.implicitHeight)
    focus: true

    property int selectedIndex: 0
    readonly property var winList: IslandBridge.minimizedWindows || []
    readonly property int windowCount: winList.length

    onWindowCountChanged: {
        if (selectedIndex >= windowCount) {
            selectedIndex = Math.max(0, windowCount - 1);
        }
    }

    // Keyboard Navigation
    Keys.onUpPressed: {
        if (selectedIndex > 0) {
            selectedIndex--;
        }
    }

    Keys.onDownPressed: {
        if (selectedIndex < windowCount - 1) {
            selectedIndex++;
        }
    }

    Keys.onReturnPressed: {
        restoreSelected();
    }

    Keys.onEnterPressed: {
        restoreSelected();
    }

    Keys.onEscapePressed: {
        IslandBridge.dismiss();
    }

    function restoreSelected() {
        if (selectedIndex >= 0 && selectedIndex < winList.length) {
            var target = winList[selectedIndex];
            if (target && target.id) {
                IslandBridge.restoreWindow(target.id);
            }
        }
    }

    Column {
        id: contentCol
        width: parent.width
        spacing: 6

        // Section Header
        Item {
            width: parent.width
            height: 22

            Row {
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                spacing: 6

                Text {
                    text: "󰖯"
                    color: Theme.accentYellow
                    font.pixelSize: 13
                    anchors.verticalCenter: parent.verticalCenter
                }

                Text {
                    text: "MINIMIZED APPLICATIONS (" + root.windowCount + ")"
                    color: Theme.textSecondary
                    font.pixelSize: 10
                    font.bold: true
                    anchors.verticalCenter: parent.verticalCenter
                }
            }

            Text {
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                text: "↑↓ Nav • ↵ Restore"
                color: Theme.textSecondary
                font.pixelSize: 9
                opacity: 0.7
            }
        }

        // Empty state
        Rectangle {
            width: parent.width
            height: 48
            radius: 8
            color: Qt.rgba(1, 1, 1, 0.04)
            visible: root.windowCount === 0

            Text {
                anchors.centerIn: parent
                text: "No applications currently minimized"
                color: Theme.textSecondary
                font.pixelSize: 11
            }
        }

        // Window Rows
        Repeater {
            model: root.winList
            delegate: Rectangle {
                id: rowDelegate
                required property int index
                required property var modelData

                width: parent.width
                height: 34
                radius: 6
                color: {
                    if (root.selectedIndex === index) return Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.25);
                    if (rowHov.hovered) return Qt.rgba(1, 1, 1, 0.12);
                    return Qt.rgba(1, 1, 1, 0.05);
                }
                border.color: (root.selectedIndex === index || rowHov.hovered) ? Theme.accent : Qt.rgba(1, 1, 1, 0.1)
                border.width: root.selectedIndex === index ? 1.5 : 1.0

                Item {
                    anchors.fill: parent
                    anchors.margins: 6

                    // App icon & title
                    Row {
                        anchors.left: parent.left
                        anchors.right: restoreBtn.left
                        anchors.rightMargin: 8
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 8

                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            text: modelData.icon || "󰖲"
                            color: Theme.accentYellow
                            font.pixelSize: 14
                        }

                        Column {
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: 1
                            width: parent.width - 24

                            Text {
                                text: modelData.title || modelData.name || modelData.app_id || "Window"
                                color: Theme.textPrimary
                                font.pixelSize: 11
                                font.bold: true
                                elide: Text.ElideRight
                                width: parent.width
                            }

                            Text {
                                text: (modelData.app_id || "application") + " • scratchpad"
                                color: Theme.textSecondary
                                font.pixelSize: 9
                                opacity: 0.8
                                elide: Text.ElideRight
                                width: parent.width
                            }
                        }
                    }

                    // Restore Action Button
                    Rectangle {
                        id: restoreBtn
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        width: 58
                        height: 20
                        radius: 4
                        color: btnHov.hovered ? Qt.lighter(Theme.accent, 1.2) : Theme.accent

                        Text {
                            anchors.centerIn: parent
                            text: "Restore"
                            color: "#ffffff"
                            font.pixelSize: 9
                            font.bold: true
                        }

                        HoverHandler { id: btnHov }
                        TapHandler {
                            onTapped: {
                                if (modelData && modelData.id) {
                                    IslandBridge.restoreWindow(modelData.id);
                                }
                            }
                        }
                    }
                }

                HoverHandler { id: rowHov }
                TapHandler {
                    onTapped: {
                        root.selectedIndex = index;
                        if (modelData && modelData.id) {
                            IslandBridge.restoreWindow(modelData.id);
                        }
                    }
                }
            }
        }
    }
}
