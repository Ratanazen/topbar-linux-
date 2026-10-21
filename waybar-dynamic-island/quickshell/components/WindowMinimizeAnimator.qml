import Quickshell
import Quickshell.Wayland
import QtQuick
import "../services"
import "../themes"

PanelWindow {
    id: animWindow

    required property var screenTarget
    screen: screenTarget

    WlrLayershell.layer: WlrLayer.Overlay
    WlrLayershell.namespace: "ratana-minimize-anim"
    WlrLayershell.keyboardFocus: WlrKeyboardFocus.None
    WlrLayershell.exclusionMode: ExclusionMode.Ignore
    exclusionMode: ExclusionMode.Ignore

    anchors.top: true
    anchors.bottom: true
    anchors.left: true
    anchors.right: true

    color: "transparent"
    visible: animCard.opacity > 0.01

    // Crucial: Only mask the animating card surface, so clicks outside are never blocked
    mask: Region {
        item: animCard.opacity > 0.05 ? animCard : null
    }

    // Active animation state
    property bool isAnimating: false
    property string animType: "minimize" // "minimize" or "restore"
    property string appIcon: "󰖲"
    property string appTitle: ""
    property int animDuration: 380

    // Coordinates
    property real startX: 0
    property real startY: 0
    property real startW: 100
    property real startH: 100
    property real startR: 12
    property real startOp: 0.9

    property real endX: 0
    property real endY: 0
    property real endW: 100
    property real endH: 100
    property real endR: 19
    property real endOp: 0.0

    Connections {
        target: IslandBridge

        function onWindowAnimationRequested(data) {
            if (!data || !data.rect) return;

            var r = data.rect;
            var w = r.width > 50 ? r.width : 640;
            var h = r.height > 50 ? r.height : 480;
            var x = r.x >= 0 ? r.x : (screenTarget.width - w) / 2;
            var y = r.y >= 0 ? r.y : 60;

            animType = data.type || "minimize";
            appIcon = data.icon || "󰖲";
            appTitle = data.title || data.app_id || "Window";
            animDuration = data.duration || 380;

            var islandX = (screenTarget.width - 180) / 2;
            var islandY = 3;
            var islandW = 180;
            var islandH = 38;

            if (animType === "minimize") {
                startX = x;
                startY = y;
                startW = w;
                startH = h;
                startR = 12;
                startOp = 0.92;

                endX = islandX;
                endY = islandY;
                endW = islandW;
                endH = islandH;
                endR = 19;
                endOp = 0.0;
            } else { // restore
                startX = islandX;
                startY = islandY;
                startW = islandW;
                startH = islandH;
                startR = 19;
                startOp = 0.05;

                endX = x;
                endY = y;
                endW = w;
                endH = h;
                endR = 12;
                endOp = 0.85;
            }

            // Reset current values
            animCard.x = startX;
            animCard.y = startY;
            animCard.width = startW;
            animCard.height = startH;
            animCard.radius = startR;
            animCard.opacity = startOp;

            cardAnim.restart();
        }
    }

    // Morphing Application Card
    Rectangle {
        id: animCard
        opacity: 0.0
        color: Theme.surface
        border.color: Theme.accent
        border.width: 1.5
        clip: true

        // Inner preview glyph & title
        Column {
            anchors.centerIn: parent
            spacing: 6
            opacity: animCard.height > 50 ? 1.0 : 0.0

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: appIcon
                font.pixelSize: Math.min(42, Math.max(16, animCard.height * 0.28))
                color: Theme.accent
            }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: appTitle
                font.pixelSize: 11
                font.bold: true
                color: Theme.textPrimary
                visible: animCard.height > 90
                elide: Text.ElideRight
                maximumLineCount: 1
            }
        }

        // Drop shadow / glow border effect
        Rectangle {
            anchors.fill: parent
            radius: parent.radius
            color: "transparent"
            border.color: Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.3)
            border.width: 3
            visible: animCard.height > 80
        }
    }

    ParallelAnimation {
        id: cardAnim

        NumberAnimation {
            target: animCard
            property: "x"
            to: endX
            duration: IslandBridge.reducedMotion ? 120 : animDuration
            easing.type: Easing.InOutCubic
        }

        NumberAnimation {
            target: animCard
            property: "y"
            to: endY
            duration: IslandBridge.reducedMotion ? 120 : animDuration
            easing.type: Easing.InOutCubic
        }

        NumberAnimation {
            target: animCard
            property: "width"
            to: endW
            duration: IslandBridge.reducedMotion ? 120 : animDuration
            easing.type: Easing.InOutCubic
        }

        NumberAnimation {
            target: animCard
            property: "height"
            to: endH
            duration: IslandBridge.reducedMotion ? 120 : animDuration
            easing.type: Easing.InOutCubic
        }

        NumberAnimation {
            target: animCard
            property: "radius"
            to: endR
            duration: IslandBridge.reducedMotion ? 120 : animDuration
            easing.type: Easing.InOutCubic
        }

        NumberAnimation {
            target: animCard
            property: "opacity"
            to: endOp
            duration: IslandBridge.reducedMotion ? 120 : animDuration
            easing.type: animType === "minimize" ? Easing.InQuad : Easing.OutQuad
        }

        onFinished: {
            animCard.opacity = 0.0;
        }
    }
}
