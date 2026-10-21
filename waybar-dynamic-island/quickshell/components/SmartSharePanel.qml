import QtQuick
import "../services"
import "../themes"

Item {
    id: root
    anchors.fill: parent
    anchors.margins: 10

    // -------------------------------------------------------------
    // Shared Computed Properties
    // -------------------------------------------------------------
    readonly property var files: IslandBridge.droppedFiles || []
    readonly property int fileCount: files.length
    readonly property var firstFile: fileCount > 0 ? files[0] : null
    readonly property string fileSummary: {
        if (fileCount === 0) return "No files selected";
        if (fileCount === 1) {
            var f = files[0];
            return f.name + (f.size_human ? " (" + f.size_human + ")" : "");
        }
        return files[0].name + " +" + (fileCount - 1) + " more file" + (fileCount > 2 ? "s" : "");
    }
    readonly property string fileIcon: {
        if (fileCount > 1) return "󰉓";
        if (firstFile && firstFile.icon) return firstFile.icon;
        return "󰈦";
    }

    // =============================================================
    // VIEW A: APP PICKER (IslandBridge.shareConfirmApp === null)
    // =============================================================
    Column {
        id: pickerView
        anchors.fill: parent
        spacing: 8
        visible: IslandBridge.shareConfirmApp === null && IslandBridge.shareStatusMessage.length === 0

        // Header Row: File Chip + Title + Close Button
        Item {
            width: parent.width
            height: 24

            Row {
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                spacing: 6

                Rectangle {
                    width: 22
                    height: 22
                    radius: 11
                    color: Qt.rgba(0, 0.82, 0.78, 0.18)
                    anchors.verticalCenter: parent.verticalCenter

                    Text {
                        anchors.centerIn: parent
                        text: root.fileIcon
                        color: Theme.accent
                        font.pixelSize: 12
                    }
                }

                Text {
                    text: root.fileSummary
                    color: Theme.textPrimary
                    font.pixelSize: 11
                    font.bold: true
                    elide: Text.ElideMiddle
                    width: Math.min(260, pickerView.width - 60)
                    anchors.verticalCenter: parent.verticalCenter
                }
            }

            Rectangle {
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                width: 20
                height: 20
                radius: 10
                color: closeHover.hovered ? Qt.rgba(1, 1, 1, 0.20) : Qt.rgba(1, 1, 1, 0.08)

                Text {
                    anchors.centerIn: parent
                    text: "✕"
                    color: Theme.textSecondary
                    font.pixelSize: 10
                }

                HoverHandler { id: closeHover }
                TapHandler { onTapped: IslandBridge.cancelShare() }
            }
        }

        // Subtitle prompt
        Text {
            text: "Select application to share with:"
            color: Theme.textSecondary
            font.pixelSize: 10
        }

        // Applications Grid (Scrollable flickable)
        Flickable {
            id: appFlickable
            width: parent.width
            height: parent.height - 70
            contentWidth: width
            contentHeight: appGrid.implicitHeight
            clip: true
            boundsBehavior: Flickable.StopAtBounds

            Grid {
                id: appGrid
                width: parent.width
                columns: 2
                spacing: 8

                Repeater {
                    model: IslandBridge.shareCandidates

                    delegate: Rectangle {
                        id: appCard
                        width: (appGrid.width - 8) / 2
                        height: 52
                        radius: 12
                        color: modelData.available ? (cardHover.hovered ? Qt.rgba(1, 1, 1, 0.14) : Theme.cardBackground) : Qt.rgba(1, 1, 1, 0.03)
                        border.color: modelData.available ? (cardHover.hovered ? Theme.accent : Qt.rgba(1, 1, 1, 0.08)) : Qt.rgba(1, 1, 1, 0.04)
                        border.width: 1
                        opacity: modelData.available ? 1.0 : 0.45

                        Row {
                            anchors.fill: parent
                            anchors.margins: 6
                            spacing: 8

                            Rectangle {
                                width: 34
                                height: 34
                                radius: 17
                                color: {
                                    if (modelData.id === "telegram") return Qt.rgba(0.18, 0.65, 0.90, 0.20);
                                    if (modelData.id === "discord") return Qt.rgba(0.35, 0.40, 0.95, 0.20);
                                    if (modelData.id === "bluetooth") return Qt.rgba(0.0, 0.50, 1.0, 0.20);
                                    return Qt.rgba(0.0, 0.82, 0.78, 0.18);
                                }
                                anchors.verticalCenter: parent.verticalCenter

                                Text {
                                    anchors.centerIn: parent
                                    text: modelData.icon || "󰒍"
                                    color: {
                                        if (modelData.id === "telegram") return "#29b6f6";
                                        if (modelData.id === "discord") return "#7289da";
                                        if (modelData.id === "bluetooth") return "#2196f3";
                                        return Theme.accent;
                                    }
                                    font.pixelSize: 16
                                }
                            }

                            Column {
                                anchors.verticalCenter: parent.verticalCenter
                                width: parent.width - 48
                                spacing: 2

                                Text {
                                    text: modelData.name || "App"
                                    color: Theme.textPrimary
                                    font.pixelSize: 11
                                    font.bold: true
                                    elide: Text.ElideRight
                                    width: parent.width
                                }

                                Text {
                                    text: modelData.reason || (modelData.available ? "Available" : "Unavailable")
                                    color: modelData.available ? Theme.textSecondary : Theme.accentRed
                                    font.pixelSize: 9
                                    elide: Text.ElideRight
                                    width: parent.width
                                }
                            }
                        }

                        HoverHandler { id: cardHover }
                        TapHandler {
                            enabled: modelData.available
                            onTapped: IslandBridge.selectShareApp(modelData)
                        }
                    }
                }
            }
        }

        // Safety Footer Notice
        Item {
            width: parent.width
            height: 16

            Row {
                anchors.centerIn: parent
                spacing: 5

                Text {
                    text: "󰌷"
                    color: Theme.accentCyan
                    font.pixelSize: 10
                    anchors.verticalCenter: parent.verticalCenter
                }
                Text {
                    text: "Safe Share: Requires confirmation before opening applications"
                    color: Theme.textSecondary
                    font.pixelSize: 9
                    anchors.verticalCenter: parent.verticalCenter
                }
            }
        }
    }

    // =============================================================
    // VIEW B: SHARE CONFIRMATION (IslandBridge.shareConfirmApp !== null)
    // =============================================================
    Column {
        id: confirmView
        anchors.fill: parent
        spacing: 10
        visible: IslandBridge.shareConfirmApp !== null && IslandBridge.shareStatusMessage.length === 0

        // Header: Target App + Close
        Item {
            width: parent.width
            height: 24

            Row {
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                spacing: 8

                Text {
                    text: IslandBridge.shareConfirmApp ? (IslandBridge.shareConfirmApp.icon || "󰒍") : "󰒍"
                    color: Theme.accent
                    font.pixelSize: 14
                    anchors.verticalCenter: parent.verticalCenter
                }

                Text {
                    text: "Confirm Share to " + (IslandBridge.shareConfirmApp ? IslandBridge.shareConfirmApp.name : "App")
                    color: Theme.textPrimary
                    font.pixelSize: 12
                    font.bold: true
                    anchors.verticalCenter: parent.verticalCenter
                }
            }

            Rectangle {
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                width: 20
                height: 20
                radius: 10
                color: confirmCloseHov.hovered ? Qt.rgba(1, 1, 1, 0.20) : Qt.rgba(1, 1, 1, 0.08)

                Text {
                    anchors.centerIn: parent
                    text: "✕"
                    color: Theme.textSecondary
                    font.pixelSize: 10
                }

                HoverHandler { id: confirmCloseHov }
                TapHandler { onTapped: IslandBridge.cancelShare() }
            }
        }

        // Target File Card Preview
        Rectangle {
            width: parent.width
            height: 48
            radius: 10
            color: Theme.cardBackground
            border.color: Qt.rgba(1, 1, 1, 0.08)
            border.width: 1

            Row {
                anchors.fill: parent
                anchors.margins: 8
                spacing: 8

                Rectangle {
                    width: 32
                    height: 32
                    radius: 16
                    color: Qt.rgba(0, 0.82, 0.78, 0.18)
                    anchors.verticalCenter: parent.verticalCenter

                    Text {
                        anchors.centerIn: parent
                        text: root.fileIcon
                        color: Theme.accent
                        font.pixelSize: 14
                    }
                }

                Column {
                    anchors.verticalCenter: parent.verticalCenter
                    width: parent.width - 48
                    spacing: 2

                    Text {
                        text: root.fileSummary
                        color: Theme.textPrimary
                        font.pixelSize: 11
                        font.bold: true
                        elide: Text.ElideMiddle
                        width: parent.width
                    }

                    Text {
                        text: "Ready to pass canonical arguments to " + (IslandBridge.shareConfirmApp ? IslandBridge.shareConfirmApp.name : "")
                        color: Theme.textSecondary
                        font.pixelSize: 9
                        elide: Text.ElideRight
                        width: parent.width
                    }
                }
            }
        }

        // Confirmation Actions Row (Back, Cancel, Confirm & Open)
        Row {
            width: parent.width
            height: 34
            spacing: 8

            // Back button
            Rectangle {
                width: 60
                height: 32
                radius: 8
                color: backHov.hovered ? Qt.rgba(1, 1, 1, 0.16) : Qt.rgba(1, 1, 1, 0.08)
                border.color: Qt.rgba(1, 1, 1, 0.10)
                border.width: 1

                Text {
                    anchors.centerIn: parent
                    text: "Back"
                    color: Theme.textSecondary
                    font.pixelSize: 11
                }

                HoverHandler { id: backHov }
                TapHandler { onTapped: IslandBridge.backToPicker() }
            }

            // Cancel button
            Rectangle {
                width: 65
                height: 32
                radius: 8
                color: cancelHov.hovered ? Qt.rgba(1, 0.27, 0.23, 0.25) : Qt.rgba(1, 1, 1, 0.08)
                border.color: Qt.rgba(1, 1, 1, 0.10)
                border.width: 1

                Text {
                    anchors.centerIn: parent
                    text: "Cancel"
                    color: cancelHov.hovered ? Theme.accentRed : Theme.textSecondary
                    font.pixelSize: 11
                }

                HoverHandler { id: cancelHov }
                TapHandler { onTapped: IslandBridge.cancelShare() }
            }

            // Spacer
            Item {
                width: parent.width - 60 - 65 - 130 - 16
                height: 1
            }

            // Confirm & Open Button
            Rectangle {
                width: 130
                height: 32
                radius: 8
                color: openHov.hovered ? Qt.darker(Theme.accent, 1.15) : Theme.accent
                border.color: Theme.accent
                border.width: 1

                Row {
                    anchors.centerIn: parent
                    spacing: 6

                    Text {
                        text: "󰌷"
                        color: "#000000"
                        font.pixelSize: 12
                        font.bold: true
                        anchors.verticalCenter: parent.verticalCenter
                    }

                    Text {
                        text: "Confirm & Open"
                        color: "#000000"
                        font.pixelSize: 11
                        font.bold: true
                        anchors.verticalCenter: parent.verticalCenter
                    }
                }

                HoverHandler { id: openHov }
                TapHandler { onTapped: IslandBridge.confirmLaunchShare() }
            }
        }

        // Explanatory note
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "Opens application with files. No silent background transmissions."
            color: Theme.textSecondary
            font.pixelSize: 9
            opacity: 0.8
        }
    }

    // =============================================================
    // VIEW C: STATUS FEEDBACK (IslandBridge.shareStatusMessage !== "")
    // =============================================================
    Item {
        id: statusView
        anchors.fill: parent
        visible: IslandBridge.shareStatusMessage.length > 0

        Column {
            anchors.centerIn: parent
            spacing: 8

            Rectangle {
                width: 44
                height: 44
                radius: 22
                color: Qt.rgba(0.19, 0.82, 0.35, 0.20)
                anchors.horizontalCenter: parent.horizontalCenter

                Text {
                    anchors.centerIn: parent
                    text: "󰄬"
                    color: Theme.accentGreen
                    font.pixelSize: 22
                }
            }

            Text {
                text: IslandBridge.shareStatusMessage
                color: Theme.textPrimary
                font.pixelSize: 12
                font.bold: true
                anchors.horizontalCenter: parent.horizontalCenter
            }

            Text {
                text: "Target application launched safely"
                color: Theme.textSecondary
                font.pixelSize: 10
                anchors.horizontalCenter: parent.horizontalCenter
            }
        }
    }
}
