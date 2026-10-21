import QtQuick
import "../services"
import "../themes"

Rectangle {
    id: root

    // Configurable Screen Placement
    anchors.top: parent.top
    anchors.topMargin: 3
    anchors.horizontalCenter: (IslandBridge.capsulePosition === "top-center" || !IslandBridge.capsulePosition) ? parent.horizontalCenter : undefined
    anchors.left: IslandBridge.capsulePosition === "top-left" ? parent.left : undefined
    anchors.leftMargin: IslandBridge.capsulePosition === "top-left" ? 24 : 0
    anchors.right: IslandBridge.capsulePosition === "top-right" ? parent.right : undefined
    anchors.rightMargin: IslandBridge.capsulePosition === "top-right" ? 24 : 0
    focus: true
    clip: true

    // Morphological Target Dimensions
    readonly property real targetWidth: {
        if (dropArea.containsDrag || contentHost.isDragHovered) {
            return 340;
        }
        var baseWidth = 180;
        switch (IslandBridge.visualState) {
            case "sharePicker": baseWidth = 460; break;
            case "dragActive": baseWidth = 340; break;
            case "settings": baseWidth = 360; break;
            case "quickActions":
            case "quick_settings": baseWidth = 380; break;
            case "expanded": baseWidth = 360; break;
            case "minimized_apps": baseWidth = 380; break;
            case "mediaExpanded":
            case "media_expanded": baseWidth = 380; break;
            case "notification": baseWidth = 360; break;
            case "bluetooth": baseWidth = 280; break;
            case "language": baseWidth = 280; break;
            case "mediaCompact":
            case "media": baseWidth = 270; break;
            case "volume":
            case "brightness": baseWidth = 260; break;
            case "timer":
            case "pomodoro": baseWidth = 240; break;
            case "task": baseWidth = 260; break;
            case "windowAnimation":
            case "minimized":
            case "restoring": baseWidth = 240; break;
            case "recording":
            case "charging":
            case "battery":
            case "battery_warning":
            case "low-battery":
            case "network":
            case "clipboard":
            case "error":
            case "system": baseWidth = 220; break;
            case "idle":
            default:
                baseWidth = Math.max(160, (contentHost.compactImplicitWidth || 130) + 32);
                break;
        }
        if (IslandBridge.showFull) {
            return baseWidth + 80;
        }
        return baseWidth;
    }

    readonly property real targetHeight: {
        if (dropArea.containsDrag || contentHost.isDragHovered) {
            return 56;
        }
        switch (IslandBridge.visualState) {
            case "sharePicker": return 330;
            case "dragActive": return 56;
            case "minimized_apps": return 240;
            case "mediaExpanded":
            case "media_expanded": return 134;
            case "expanded": return (IslandBridge.minimizedWindows && IslandBridge.minimizedWindows.length > 0) ? 142 : 126;
            case "settings": return 118;
            case "quickActions":
            case "quick_settings": return 220;
            case "notification": return 60;
            case "volume":
            case "brightness":
            case "bluetooth": return 40;
            case "timer":
            case "pomodoro":
            case "recording":
            case "mediaCompact":
            case "media":
            case "windowAnimation":
            case "minimized":
            case "restoring":
            case "idle":
            default:
                return 38;
        }
    }

    readonly property real targetRadius: {
        if (dropArea.containsDrag || contentHost.isDragHovered) {
            return 22;
        }
        switch (IslandBridge.visualState) {
            case "sharePicker": return 24;
            case "dragActive": return 22;
            case "minimized_apps": return 22;
            case "mediaExpanded":
            case "media_expanded": return 24;
            case "expanded": return 22;
            case "settings": return 20;
            case "quickActions":
            case "quick_settings": return 22;
            case "notification": return 20;
            default: return 19;
        }
    }

    width: targetWidth
    height: targetHeight
    radius: targetRadius

    // Fallback crisp opaque glass styling when compositor blur is disabled or unsupported
    color: IslandBridge.blurEnabled ? Theme.background : Qt.rgba(0.08, 0.08, 0.1, 0.98)
    border.color: {
        if (dropArea.containsDrag || contentHost.isDragHovered || IslandBridge.visualState === "dragActive")
            return Theme.accent;
        if (IslandBridge.visualState === "sharePicker")
            return Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.45);
        if (IslandBridge.visualState === "recording")
            return Theme.accentRed;
        return capsuleHover.hovered ? Theme.accent : Theme.border;
    }
    border.width: (dropArea.containsDrag || contentHost.isDragHovered || IslandBridge.visualState === "dragActive" || IslandBridge.visualState === "recording") ? 1.5 : 1.0

    // Smooth Spring Morphing Transitions
    Behavior on width {
        NumberAnimation {
            duration: IslandBridge.reducedMotion ? 0 : 280
            easing.type: Easing.OutBack
            easing.overshoot: 1.05
        }
    }

    Behavior on height {
        NumberAnimation {
            duration: IslandBridge.reducedMotion ? 0 : 250
            easing.type: Easing.OutCubic
        }
    }

    Behavior on radius {
        NumberAnimation {
            duration: IslandBridge.reducedMotion ? 0 : 250
            easing.type: Easing.OutCubic
        }
    }

    Behavior on border.color {
        ColorAnimation { duration: 180 }
    }

    // Keyboard Accessibility: Esc closes expanded panels
    Keys.onEscapePressed: {
        IslandBridge.dismiss();
    }

    // Drag and Drop Zone
    DropArea {
        id: dropArea
        anchors.fill: parent
        keys: ["text/uri-list", "text/plain"]

        onEntered: drag => {
            if (drag.hasUrls || drag.hasText) {
                contentHost.isDragHovered = true;
                drag.acceptProposedAction();
            }
        }

        onExited: {
            contentHost.isDragHovered = false;
        }

        onDropped: drop => {
            contentHost.isDragHovered = false;
            var urls = [];
            if (drop.hasUrls && drop.urls.length > 0) {
                for (var i = 0; i < drop.urls.length; i++) {
                    urls.push(drop.urls[i].toString());
                }
            } else if (drop.hasText && drop.text.length > 0) {
                urls.push(drop.text);
            }
            if (urls.length > 0) {
                drop.acceptProposedAction();
                IslandBridge.inspectFiles(urls);
            }
        }
    }

    // Interactive Mouse & Touch Handler (only active for non-complex panels)
    HoverHandler {
        id: capsuleHover
    }

    MouseArea {
        anchors.fill: parent
        acceptedButtons: Qt.LeftButton | Qt.RightButton | Qt.MiddleButton
        hoverEnabled: false
        enabled: IslandBridge.visualState !== "sharePicker" && IslandBridge.visualState !== "settings" && IslandBridge.visualState !== "quickActions"

        onClicked: mouse => {
            if (mouse.button === Qt.RightButton) {
                IslandBridge.toggleQuickActions();
            } else if (mouse.button === Qt.MiddleButton) {
                IslandBridge.toggleMedia();
            } else {
                if (IslandBridge.visualState === "mediaCompact" || IslandBridge.visualState === "mediaExpanded" || IslandBridge.visualState === "media") {
                    IslandBridge.toggleExpanded();
                } else if (IslandBridge.visualState === "notification") {
                    IslandBridge.dismiss();
                } else if (IslandBridge.visualState === "bluetooth") {
                    IslandBridge.sendCommand("bluetooth", ["scan"]);
                } else if (IslandBridge.visualState === "idle") {
                    IslandBridge.toggleQuickActions();
                }
            }
        }

        onWheel: wheel => {
            if (wheel.angleDelta.y > 0) {
                IslandBridge.volumeUp();
            } else if (wheel.angleDelta.y < 0) {
                IslandBridge.volumeDown();
            }
        }
    }

    // Dynamic Island Content
    IslandContent {
        id: contentHost
    }
}
