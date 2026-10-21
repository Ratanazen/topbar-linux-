import Quickshell
import Quickshell.Wayland
import QtQuick
import QtQuick.Shapes
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
    visible: isAnimating

    // Wayland Input Mask: Only mask active elements during animation; zero interception outside
    mask: Region {
        item: isAnimating ? (isLampStyle ? lampBoundingBox : animCard) : null
    }

    // Active animation state
    property bool isAnimating: false
    property real animProgress: 0.0
    property string animType: "minimize" // "minimize" or "restore"
    property string animStyle: "macos-lamp" // "macos-lamp", "lamp", "macos-genie-inspired", "genie", "spring-scale", "scale-fade", "reduced-motion", "none", "low-resource"
    property string animTarget: "island" // "island" or "dock"
    property string appIcon: "󰖲"
    property string appTitle: ""
    property string thumbnailPath: ""
    property int animDuration: 420
    property int animWindowId: 0

    readonly property bool isLampStyle: animStyle === "macos-lamp" ||
                                        animStyle === "lamp" ||
                                        animStyle === "macos-genie-inspired" ||
                                        animStyle === "genie" ||
                                        animStyle === "magic-lamp"

    // Normalized progress: 0.0 = full window on desktop; 1.0 = fully inside island/dock
    readonly property real normT: animType === "minimize" ? animProgress : (1.0 - animProgress)

    // Base coordinates
    property real startX: 0
    property real startY: 0
    property real startW: 100
    property real startH: 100
    property real startR: 12
    property real startOp: 0.95

    property real endX: 0
    property real endY: 0
    property real endW: 100
    property real endH: 100
    property real endR: 19
    property real endOp: 0.0

    // Original window bounds on desktop
    readonly property real winOrigX: animType === "minimize" ? startX : endX
    readonly property real winOrigY: animType === "minimize" ? startY : endY
    readonly property real winOrigW: animType === "minimize" ? startW : endW
    readonly property real winOrigH: animType === "minimize" ? startH : endH

    // Target mouth coordinates (Dynamic Island capsule center or Dock center)
    readonly property real islandMouthX: {
        var baseDestX = animType === "minimize" ? endX : startX;
        var baseDestW = animType === "minimize" ? endW : startW;
        return baseDestX + baseDestW / 2;
    }
    readonly property real islandMouthY: {
        var baseDestY = animType === "minimize" ? endY : startY;
        var baseDestH = animType === "minimize" ? endH : startH;
        return animTarget === "dock" ? baseDestY : (baseDestY + baseDestH);
    }

    // ========================================================
    // MAGIC LAMP EFFECT GEOMETRY (macOS Genie Funnel Profile)
    // ========================================================
    readonly property real lampCenterX: winOrigX + winOrigW / 2 + (islandMouthX - (winOrigX + winOrigW / 2)) * Math.pow(normT, 1.15)
    readonly property real lampTopY: Math.max(islandMouthY - 6, winOrigY + (islandMouthY - winOrigY) * Math.pow(normT, 0.82))
    readonly property real lampBottomY: Math.max(lampTopY + 16, (winOrigY + winOrigH) + ((islandMouthY + 10) - (winOrigY + winOrigH)) * Math.pow(normT, 1.35))

    readonly property real lampTopW: Math.max(34, winOrigW + (50 - winOrigW) * Math.pow(normT, 0.68))
    readonly property real lampBottomW: Math.max(34, winOrigW + (50 - winOrigW) * Math.pow(normT, 1.32))

    // Asymmetric hourglass waist pinch (Image 2 - Aladdin magic lamp curve)
    readonly property real lampWaistPinch: 0.34 * Math.sin(normT * Math.PI)
    readonly property real lampWaistY: lampTopY + (lampBottomY - lampTopY) * 0.36
    readonly property real lampWaistW: Math.max(26, Math.min(lampTopW, lampBottomW) * (1.0 - lampWaistPinch))

    readonly property real topLeftX: lampCenterX - lampTopW / 2
    readonly property real topRightX: lampCenterX + lampTopW / 2
    readonly property real bottomLeftX: lampCenterX - lampBottomW / 2
    readonly property real bottomRightX: lampCenterX + lampBottomW / 2
    readonly property real waistLeftX: lampCenterX - lampWaistW / 2
    readonly property real waistRightX: lampCenterX + lampWaistW / 2

    // Dynamic bounding box for Wayland click masking
    Item {
        id: lampBoundingBox
        x: Math.min(topLeftX, bottomLeftX, islandMouthX - 40) - 20
        y: Math.min(islandMouthY, lampTopY) - 10
        width: Math.max(lampTopW, lampBottomW, 140) + 40
        height: Math.max(lampBottomY - lampTopY, 60) + 40
    }

    Connections {
        target: IslandBridge

        function onWindowAnimationRequested(data) {
            if (!data || !data.rect) return;

            // Multi-monitor matching: if target output is known, only animate on matching screen
            if (data.output && screenTarget && screenTarget.name && data.output !== screenTarget.name) {
                return;
            }

            if (cardAnim.running) {
                cardAnim.stop();
            }

            var r = data.rect;
            var w = r.width > 50 ? r.width : 640;
            var h = r.height > 50 ? r.height : 480;
            var x = r.x >= 0 ? r.x : (screenTarget.width - w) / 2;
            var y = r.y >= 0 ? r.y : 60;

            animWindowId = data.id || 0;

            animType = data.type || "minimize";
            animStyle = (data.style || "macos-lamp").toLowerCase();
            animTarget = (data.target || "island").toLowerCase();
            appIcon = data.icon || "󰖲";
            appTitle = data.title || data.app_id || "Window";
            thumbnailPath = data.thumbnail || "";
            animDuration = data.duration || 420;

            // Target destination coordinates (Island capsule center or Dock)
            var destX = (screenTarget.width - 180) / 2;
            var destY = 3;
            var destW = 180;
            var destH = 38;
            var destR = 19;

            if (animTarget === "dock") {
                destX = (screenTarget.width - 340) / 2;
                destY = screenTarget.height - 62;
                destW = 340;
                destH = 50;
                destR = 18;
            }

            if (animType === "minimize") {
                startX = x;
                startY = y;
                startW = w;
                startH = h;
                startR = 12;
                startOp = 0.95;

                endX = destX;
                endY = destY;
                endW = destW;
                endH = destH;
                endR = destR;
                endOp = 0.0;
            } else { // restore
                startX = destX;
                startY = destY;
                startW = destW;
                startH = destH;
                startR = destR;
                startOp = 0.2;

                endX = x;
                endY = y;
                endW = w;
                endH = h;
                endR = 12;
                endOp = 1.0;

                // On restore, emit immediate absorption pulse from island mouth
                IslandBridge.triggerAbsorptionPulse();
            }

            // Fallback rectangular card initialization
            animCard.x = startX;
            animCard.y = startY;
            animCard.width = startW;
            animCard.height = startH;
            animCard.radius = startR;
            animCard.opacity = startOp;

            if (animStyle === "none") {
                animCard.opacity = 0.0;
                isAnimating = false;
                return;
            }

            isAnimating = true;
            animProgress = 0.0;
            cardAnim.restart();
        }
    }

    // ========================================================
    // 1. MAGIC LAMP FUNNEL & LUMINOUS BEAM (Image 1 & Image 2)
    // ========================================================
    Item {
        id: lampContainer
        anchors.fill: parent
        visible: isAnimating && isLampStyle && (animType === "restore" ? (normT <= 1.0) : (normT < 0.98))
        opacity: Math.max(0.0, Math.min(1.0, (1.0 - normT * 0.95) * 1.5))

        // A. Luminous Suction Beam (Ray connecting Island to Window Top, Image 1 Step 2)
        Shape {
            anchors.fill: parent
            visible: normT > 0.02 && normT < 0.96

            // Layer 1: Ethereal Aurora Halo Glow
            ShapePath {
                strokeWidth: Math.min(32, Math.max(14, (1.0 - normT) * 26 + 10))
                strokeColor: Qt.rgba(0.0, 0.85, 1.0, 0.28 * Math.sin(normT * Math.PI))
                fillColor: "transparent"
                startX: islandMouthX; startY: islandMouthY
                PathCubic {
                    x: lampCenterX; y: lampTopY
                    control1X: islandMouthX; control1Y: islandMouthY + (lampTopY - islandMouthY) * 0.45
                    control2X: lampCenterX; control2Y: lampTopY - (lampTopY - islandMouthY) * 0.35
                }
            }

            // Layer 2: Radiant Cyan Body Stream
            ShapePath {
                strokeWidth: Math.min(10, Math.max(4, (1.0 - normT) * 9 + 3))
                strokeColor: Qt.rgba(0.2, 0.95, 1.0, 0.82)
                fillColor: "transparent"
                startX: islandMouthX; startY: islandMouthY
                PathCubic {
                    x: lampCenterX; y: lampTopY
                    control1X: islandMouthX; control1Y: islandMouthY + (lampTopY - islandMouthY) * 0.45
                    control2X: lampCenterX; control2Y: lampTopY - (lampTopY - islandMouthY) * 0.35
                }
            }

            // Layer 3: Laser White Core Highlight
            ShapePath {
                strokeWidth: 2.2
                strokeColor: Qt.rgba(1.0, 1.0, 1.0, 0.95)
                fillColor: "transparent"
                startX: islandMouthX; startY: islandMouthY
                PathCubic {
                    x: lampCenterX; y: lampTopY
                    control1X: islandMouthX; control1Y: islandMouthY + (lampTopY - islandMouthY) * 0.45
                    control2X: lampCenterX; control2Y: lampTopY - (lampTopY - islandMouthY) * 0.35
                }
            }
        }

        // B. Island Mouth Flare (Glowing aura at capsule mouth)
        Rectangle {
            x: islandMouthX - width / 2
            y: islandMouthY - height / 2
            width: Math.min(160, Math.max(44, (1.0 - normT) * 120 + 36))
            height: 18
            radius: 9
            color: Qt.rgba(0.0, 0.9, 1.0, 0.45 * Math.sin(normT * Math.PI))
            border.color: Qt.rgba(1, 1, 1, 0.75)
            border.width: 1
            visible: normT > 0.03 && normT < 0.97
        }

        // C. Window Top Suction Cap (Flare where ray enters the window)
        Rectangle {
            x: lampCenterX - width / 2
            y: lampTopY - height / 2
            width: Math.min(lampTopW * 0.85, 96)
            height: 10
            radius: 5
            color: Qt.rgba(0.0, 0.95, 1.0, 0.65)
            border.color: "#ffffff"
            border.width: 1
            visible: normT > 0.02 && normT < 0.96
        }

        // D. Magic Lamp Curved Body Silhouette (Image 2)
        Shape {
            anchors.fill: parent

            ShapePath {
                strokeWidth: 2.0
                strokeGradient: LinearGradient {
                    x1: topLeftX; y1: lampTopY; x2: bottomRightX; y2: lampBottomY
                    GradientStop { position: 0.0; color: "#00f0ff" }
                    GradientStop { position: 0.45; color: "#a855f7" }
                    GradientStop { position: 1.0; color: "#3b82f6" }
                }
                fillGradient: LinearGradient {
                    x1: 0; y1: lampTopY; x2: 0; y2: lampBottomY
                    GradientStop { position: 0.0; color: Qt.rgba(0.12, 0.12, 0.22, 0.92) }
                    GradientStop { position: 1.0; color: Qt.rgba(0.06, 0.06, 0.12, 0.96) }
                }

                startX: topLeftX; startY: lampTopY
                PathLine { x: topRightX; y: lampTopY }
                PathCubic {
                    x: bottomRightX; y: lampBottomY
                    control1X: waistRightX; control1Y: lampTopY + (lampWaistY - lampTopY) * 0.5
                    control2X: waistRightX; control2Y: lampWaistY + (lampBottomY - lampWaistY) * 0.5
                }
                PathLine { x: bottomLeftX; y: lampBottomY }
                PathCubic {
                    x: topLeftX; y: lampTopY
                    control1X: waistLeftX; control1Y: lampWaistY + (lampBottomY - lampWaistY) * 0.5
                    control2X: waistLeftX; control2Y: lampTopY + (lampWaistY - lampTopY) * 0.5
                }
            }
        }

        // E. Real Window Thumbnail Snapshot Preview
        Image {
            id: lampThumb
            x: lampCenterX - Math.max(lampTopW, lampBottomW) / 2
            y: lampTopY
            width: Math.max(lampTopW, lampBottomW)
            height: Math.max(24, lampBottomY - lampTopY)
            source: (thumbnailPath && animStyle !== "low-resource") ? ("file://" + thumbnailPath) : ""
            fillMode: Image.PreserveAspectCrop
            visible: status === Image.Ready && animStyle !== "low-resource" && thumbnailPath.length > 0
            opacity: Math.max(0.0, 0.88 * (1.0 - normT * 0.85))
            clip: true
        }

        // F. Centered App Icon & Title Badge inside Lamp Body
        Column {
            x: lampCenterX - width / 2
            y: lampTopY + (lampBottomY - lampTopY) * 0.42 - height / 2
            spacing: 4
            visible: (lampBottomY - lampTopY) > 42
            opacity: Math.max(0.0, 1.0 - normT * 1.15)

            Rectangle {
                anchors.horizontalCenter: parent.horizontalCenter
                width: lampBadgeCol.implicitWidth + 22
                height: lampBadgeCol.implicitHeight + 10
                radius: 12
                color: Qt.rgba(0.08, 0.08, 0.14, 0.85)
                border.color: Qt.rgba(255, 255, 255, 0.20)
                border.width: 1

                Column {
                    id: lampBadgeCol
                    anchors.centerIn: parent
                    spacing: 3

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: appIcon
                        font.pixelSize: Math.min(36, Math.max(16, (lampBottomY - lampTopY) * 0.24))
                        color: Theme.accentYellow
                    }

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: appTitle
                        font.pixelSize: 11
                        font.bold: true
                        color: Theme.textPrimary
                        visible: (lampBottomY - lampTopY) > 85
                        elide: Text.ElideRight
                        maximumLineCount: 1
                    }
                }
            }
        }
    }

    // ========================================================
    // 2. FALLBACK RECTANGULAR CARD (For non-lamp styles)
    // ========================================================
    Rectangle {
        id: animCard
        visible: !isLampStyle && animCard.opacity > 0.01
        opacity: 0.0
        color: Theme.surface
        border.color: Theme.accent
        border.width: animStyle === "low-resource" ? 1.0 : 1.5
        clip: true

        Image {
            id: windowThumbnail
            anchors.fill: parent
            source: (thumbnailPath && animStyle !== "low-resource") ? ("file://" + thumbnailPath) : ""
            fillMode: Image.PreserveAspectCrop
            visible: status === Image.Ready && animStyle !== "low-resource"
            opacity: 0.92
        }

        Column {
            anchors.centerIn: parent
            spacing: 6
            opacity: animCard.height > 45 ? 1.0 : 0.0

            Rectangle {
                anchors.horizontalCenter: parent.horizontalCenter
                width: badgeCol.implicitWidth + 24
                height: badgeCol.implicitHeight + 12
                radius: 12
                color: windowThumbnail.visible ? Qt.rgba(0.08, 0.08, 0.12, 0.85) : "transparent"
                border.color: windowThumbnail.visible ? Qt.rgba(255, 255, 255, 0.15) : "transparent"
                border.width: windowThumbnail.visible ? 1 : 0

                Column {
                    id: badgeCol
                    anchors.centerIn: parent
                    spacing: 4

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: appIcon
                        font.pixelSize: Math.min(38, Math.max(16, animCard.height * 0.25))
                        color: Theme.accentYellow
                    }

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: appTitle
                        font.pixelSize: 11
                        font.bold: true
                        color: Theme.textPrimary
                        visible: animCard.height > 85
                        elide: Text.ElideRight
                        maximumLineCount: 1
                    }
                }
            }
        }

        Rectangle {
            anchors.fill: parent
            radius: parent.radius
            color: "transparent"
            border.color: Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.3)
            border.width: 2.5
            visible: animCard.height > 75 && animStyle !== "low-resource"
        }
    }

    readonly property int effectiveDuration: {
        if (animStyle === "none") return 0;
        if (animStyle === "reduced-motion" || IslandBridge.reducedMotion) return 80;
        if (animStyle === "low-resource") return 120;
        if (animStyle === "hyperos-mini") return 180;
        return animDuration;
    }

    readonly property var xEasing: {
        if (animStyle === "spring-scale" || animStyle === "originos-spring" || animStyle === "spring")
            return Easing.OutBack;
        if (animStyle === "scale-fade")
            return Easing.InOutQuad;
        if (animStyle === "hyperos-mini")
            return Easing.OutQuad;
        if (animStyle === "low-resource")
            return Easing.Linear;
        return Easing.InOutCubic;
    }

    readonly property var yEasing: {
        if (animStyle === "spring-scale" || animStyle === "originos-spring" || animStyle === "spring")
            return Easing.OutBack;
        if (animStyle === "scale-fade")
            return Easing.InOutQuad;
        if (animStyle === "hyperos-mini")
            return Easing.OutQuad;
        if (animStyle === "low-resource")
            return Easing.Linear;
        return Easing.InOutCubic;
    }

    readonly property var widthEasing: {
        if (animStyle === "spring-scale" || animStyle === "originos-spring" || animStyle === "spring")
            return Easing.OutBack;
        if (animStyle === "scale-fade")
            return Easing.InOutQuad;
        if (animStyle === "hyperos-mini")
            return Easing.OutQuad;
        if (animStyle === "low-resource")
            return Easing.Linear;
        return Easing.InOutCubic;
    }

    // Master Animation Controller
    ParallelAnimation {
        id: cardAnim

        // 1. Progress driver for Magic Lamp funnel & suction beam
        NumberAnimation {
            target: animWindow
            property: "animProgress"
            from: 0.0
            to: 1.0
            duration: effectiveDuration
            easing.type: Easing.InOutCubic
        }

        // 2. Rectangular card coordinate animations for fallback styles
        NumberAnimation {
            target: animCard
            property: "x"
            to: (animStyle === "reduced-motion" || IslandBridge.reducedMotion) ? startX : endX
            duration: effectiveDuration
            easing.type: xEasing
            easing.overshoot: (animStyle === "spring-scale" || animStyle === "originos-spring" || animStyle === "spring") ? 1.35 : 1.0
        }

        NumberAnimation {
            target: animCard
            property: "y"
            to: (animStyle === "reduced-motion" || IslandBridge.reducedMotion) ? startY : endY
            duration: effectiveDuration
            easing.type: yEasing
            easing.overshoot: (animStyle === "spring-scale" || animStyle === "originos-spring" || animStyle === "spring") ? 1.35 : 1.0
        }

        NumberAnimation {
            target: animCard
            property: "width"
            to: (animStyle === "reduced-motion" || IslandBridge.reducedMotion) ? startW : endW
            duration: effectiveDuration
            easing.type: widthEasing
        }

        NumberAnimation {
            target: animCard
            property: "height"
            to: (animStyle === "reduced-motion" || IslandBridge.reducedMotion) ? startH : endH
            duration: effectiveDuration
            easing.type: Easing.InOutCubic
        }

        NumberAnimation {
            target: animCard
            property: "radius"
            to: endR
            duration: effectiveDuration
            easing.type: (animStyle === "originos-morph" || animStyle === "morph") ? Easing.InOutBack : Easing.InOutCubic
        }

        NumberAnimation {
            target: animCard
            property: "opacity"
            to: endOp
            duration: effectiveDuration
            easing.type: (animStyle === "scale-fade" || animType === "minimize") ? Easing.InQuad : Easing.OutQuad
        }

        onFinished: {
            // Step 3 (Image 1): App enters Dynamic Island — trigger absorption pulse!
            if (animType === "minimize") {
                IslandBridge.triggerAbsorptionPulse();
            } else if (animType === "restore") {
                IslandBridge.notifyRestoreFinished(animWindowId);
            }
            animCard.opacity = 0.0;
            isAnimating = false;
            animProgress = 0.0;
        }
    }
}
