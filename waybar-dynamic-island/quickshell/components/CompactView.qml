import QtQuick
import "../services"
import "../themes"

Row {
    id: root
    anchors.centerIn: parent
    spacing: 8

    // 1. Standard Idle Presentation (Shown when no apps are minimized)
    Row {
        id: idleClockRow
        spacing: 6
        anchors.verticalCenter: parent.verticalCenter
        visible: !IslandBridge.minimizedWindows || IslandBridge.minimizedWindows.length === 0

        TapHandler {
            onTapped: IslandBridge.toggleQuickActions()
            onLongPressed: IslandBridge.toggleQuickActions()
        }

        Image {
            id: compAppSvg
            width: 14
            height: 14
            anchors.verticalCenter: parent.verticalCenter
            source: (IslandBridge.focusedWindow && IslandBridge.focusedWindow.icon_path) ? ("file://" + IslandBridge.focusedWindow.icon_path) : ((IslandBridge.iconPath && IslandBridge.iconPath.length > 0) ? ("file://" + IslandBridge.iconPath) : "")
            fillMode: Image.PreserveAspectFit
            visible: status === Image.Ready && source.toString().length > 0
            asynchronous: true
            cache: true
        }

        Text {
            text: (IslandBridge.focusedWindow && IslandBridge.focusedWindow.icon) ? IslandBridge.focusedWindow.icon : (IslandBridge.icon || "󰸗")
            color: Theme.accent
            font.pixelSize: 13
            font.family: Theme.fontFamily
            anchors.verticalCenter: parent.verticalCenter
            visible: !compAppSvg.visible
        }

        Text {
            text: {
                if (IslandBridge.focusedWindow && (IslandBridge.focusedWindow.name || IslandBridge.focusedWindow.title)) {
                    var appName = IslandBridge.focusedWindow.name || IslandBridge.focusedWindow.title;
                    if (appName.length > 22) appName = appName.substring(0, 20) + "…";
                    return appName + "  •  " + (IslandBridge.title || "");
                }
                return IslandBridge.title || "";
            }
            color: Theme.textPrimary
            font.pixelSize: 12
            font.bold: true
            anchors.verticalCenter: parent.verticalCenter
        }
    }

    // 2. iOS SINGLE-CAPSULE APP MINIMIZE: ONE shared capsule showing ONLY the selected application
    Row {
        id: singleAppCapsule
        spacing: 6
        anchors.verticalCenter: parent.verticalCenter
        visible: IslandBridge.minimizedWindows && IslandBridge.minimizedWindows.length > 0

        TapHandler {
            onTapped: IslandBridge.toggleQuickActions()
            onLongPressed: IslandBridge.toggleQuickActions()
        }

        // Optional clock pill when showFull is enabled
        Row {
            spacing: 5
            anchors.verticalCenter: parent.verticalCenter
            visible: IslandBridge.showFull

            Text {
                text: IslandBridge.title ? IslandBridge.title.split("•")[0].trim() : ""
                color: Theme.textSecondary
                font.pixelSize: 11
                anchors.verticalCenter: parent.verticalCenter
            }

            Rectangle {
                width: 1
                height: 12
                color: Qt.rgba(1, 1, 1, 0.2)
                anchors.verticalCenter: parent.verticalCenter
            }
        }

        // Previous application chevron (visible when more than 1 app is minimized)
        Rectangle {
            width: 16
            height: 20
            radius: 8
            color: prevHov.hovered ? Qt.rgba(1, 1, 1, 0.15) : "transparent"
            visible: IslandBridge.minimizedWindows && IslandBridge.minimizedWindows.length > 1
            anchors.verticalCenter: parent.verticalCenter

            Text {
                anchors.centerIn: parent
                text: "‹"
                font.pixelSize: 14
                font.bold: true
                color: prevHov.hovered ? Theme.accent : Theme.textSecondary
            }

            HoverHandler { id: prevHov }
            TapHandler {
                onTapped: IslandBridge.prevMinimizedWindow()
            }
        }

        // Single Selected App Pill: Icon + Title
        Rectangle {
            id: selectedAppPill
            height: 24
            implicitWidth: appPillRow.implicitWidth + 14
            radius: 12
            color: pillHov.hovered ? Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.22) : Qt.rgba(1, 1, 1, 0.08)
            border.color: pillHov.hovered ? Theme.accent : Qt.rgba(1, 1, 1, 0.14)
            border.width: 1
            anchors.verticalCenter: parent.verticalCenter

            Row {
                id: appPillRow
                anchors.centerIn: parent
                spacing: 6

                // App Icon (Clicking triggers restore animation)
                Item {
                    width: 15
                    height: 15
                    anchors.verticalCenter: parent.verticalCenter

                    Image {
                        id: minAppSvg
                        anchors.fill: parent
                        source: (IslandBridge.selectedMinimizedWindow && IslandBridge.selectedMinimizedWindow.icon_path) ? ("file://" + IslandBridge.selectedMinimizedWindow.icon_path) : ""
                        fillMode: Image.PreserveAspectFit
                        visible: status === Image.Ready && source.toString().length > 0
                        asynchronous: true
                        cache: true
                    }

                    Text {
                        anchors.centerIn: parent
                        text: IslandBridge.selectedMinimizedWindow ? (IslandBridge.selectedMinimizedWindow.icon || "󰖲") : "󰖲"
                        color: Theme.accentYellow
                        font.pixelSize: 13
                        font.family: Theme.fontFamily
                        visible: !minAppSvg.visible
                    }

                    scale: pillHov.hovered ? 1.15 : 1.0
                    Behavior on scale {
                        NumberAnimation { duration: 150; easing.type: Easing.OutBack }
                    }

                    TapHandler {
                        onTapped: IslandBridge.restoreSelectedWindow()
                    }
                }

                // App Title
                Text {
                    text: IslandBridge.selectedMinimizedWindow ? (IslandBridge.selectedMinimizedWindow.name || IslandBridge.selectedMinimizedWindow.title || IslandBridge.selectedMinimizedWindow.app_id || "App") : ""
                    color: Theme.textPrimary
                    font.pixelSize: 11
                    font.bold: true
                    elide: Text.ElideRight
                    maximumLineCount: 1
                    width: Math.min(100, implicitWidth)
                    anchors.verticalCenter: parent.verticalCenter
                }
            }

            HoverHandler { id: pillHov }
            TapHandler {
                onTapped: {
                    IslandBridge.toggleQuickActions();
                }
                onLongPressed: {
                    IslandBridge.toggleQuickActions();
                }
            }

            WheelHandler {
                onWheel: event => {
                    if (event.angleDelta.y > 0) {
                        IslandBridge.prevMinimizedWindow();
                    } else if (event.angleDelta.y < 0) {
                        IslandBridge.nextMinimizedWindow();
                    }
                }
            }
        }

        // Counter badge: e.g. "1/3" (Clicking expands compact app selector)
        Rectangle {
            id: counterBadge
            width: counterText.implicitWidth + 10
            height: 18
            radius: 9
            color: counterHov.hovered ? Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.35) : Qt.rgba(1, 1, 1, 0.12)
            border.color: counterHov.hovered ? Theme.accent : Qt.rgba(1, 1, 1, 0.2)
            border.width: 1
            anchors.verticalCenter: parent.verticalCenter

            Text {
                id: counterText
                anchors.centerIn: parent
                text: "" + ((IslandBridge.selectedMinimizedIndex || 0) + 1) + "/" + (IslandBridge.minimizedWindows ? IslandBridge.minimizedWindows.length : 1)
                color: counterHov.hovered ? "#ffffff" : Theme.textSecondary
                font.pixelSize: 9
                font.bold: true
            }

            HoverHandler { id: counterHov }
            TapHandler {
                onTapped: {
                    IslandBridge.sendCommand("windows", ["manager"]);
                }
            }
        }

        // Next application chevron (visible when more than 1 app is minimized)
        Rectangle {
            width: 16
            height: 20
            radius: 8
            color: nextHov.hovered ? Qt.rgba(1, 1, 1, 0.15) : "transparent"
            visible: IslandBridge.minimizedWindows && IslandBridge.minimizedWindows.length > 1
            anchors.verticalCenter: parent.verticalCenter

            Text {
                anchors.centerIn: parent
                text: "›"
                font.pixelSize: 14
                font.bold: true
                color: nextHov.hovered ? Theme.accent : Theme.textSecondary
            }

            HoverHandler { id: nextHov }
            TapHandler {
                onTapped: IslandBridge.nextMinimizedWindow()
            }
        }
    }
}
