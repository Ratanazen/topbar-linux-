import QtQuick
import "../services"
import "../themes"

Row {
    id: root
    anchors.centerIn: parent
    spacing: 10

    // Status Icon
    Rectangle {
        width: 22
        height: 22
        radius: 11
        color: {
            if (IslandBridge.visualState === "battery_warning" || IslandBridge.visualState === "low-battery")
                return Qt.rgba(1, 0.27, 0.23, 0.2);
            if (IslandBridge.visualState === "charging")
                return Qt.rgba(0.19, 0.82, 0.35, 0.2);
            return Qt.rgba(1, 1, 1, 0.08);
        }
        anchors.verticalCenter: parent.verticalCenter

        Text {
            anchors.centerIn: parent
            text: IslandBridge.icon || "󰋼"
            color: {
                if (IslandBridge.visualState === "battery_warning" || IslandBridge.visualState === "low-battery")
                    return Theme.accentRed;
                if (IslandBridge.visualState === "charging")
                    return Theme.accentGreen;
                return Theme.accent;
            }
            font.pixelSize: 13
        }
    }

    // Title & Subtitle or Progress
    Column {
        anchors.verticalCenter: parent.verticalCenter
        spacing: 1

        Text {
            text: IslandBridge.title || ""
            color: Theme.textPrimary
            font.pixelSize: 12
            font.bold: true
        }

        Text {
            visible: text.length > 0
            text: IslandBridge.subtitle || ""
            color: Theme.textSecondary
            font.pixelSize: 10
            elide: Text.ElideRight
            maximumLineCount: 1
        }
    }
}
