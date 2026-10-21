import Quickshell
import Quickshell.Wayland
import QtQuick
import "components"
import "services"
import "themes"
import "dock"

ShellRoot {
    id: root

    // 0. macOS-Style Top Bar (Tahoe Inspired Full Menu Bar)
    Variants {
        model: Quickshell.screens

        delegate: Component {
            MacTopBar {
                id: topBar
                required property var modelData
                screenTarget: modelData
            }
        }
    }

    // 1. Dynamic Island Top Layer-Shell Overlay
    Variants {
        model: Quickshell.screens


        delegate: Component {
            PanelWindow {
                id: islandOverlay
                required property var modelData
                screen: modelData

                // Layer Shell Protocol Properties (Overlay guarantees clicks reach dynamic island over Waybar)
                WlrLayershell.layer: WlrLayer.Overlay
                WlrLayershell.namespace: "ratana-island"
                WlrLayershell.keyboardFocus: (IslandBridge.userExpanded || IslandBridge.quickActionsOpen || IslandBridge.settingsOpen || IslandBridge.wifiOpen || IslandBridge.bluetoothOpen) ? WlrKeyboardFocus.OnDemand : WlrKeyboardFocus.None
                WlrLayershell.exclusionMode: ExclusionMode.Ignore
                exclusionMode: ExclusionMode.Ignore

                readonly property bool isExpanded: IslandBridge.userExpanded ||
                                                    IslandBridge.quickActionsOpen ||
                                                    IslandBridge.settingsOpen ||
                                                    IslandBridge.wifiOpen ||
                                                    IslandBridge.bluetoothOpen ||
                                                    IslandBridge.visualState === "quickActions" ||
                                                    IslandBridge.visualState === "settings" ||
                                                    IslandBridge.visualState === "wifi" ||
                                                    IslandBridge.visualState === "bluetooth" ||
                                                    IslandBridge.activeState === "share_picker"

                // Anchor to top edge with full width (and bottom when expanded for full off-click dismiss area)
                anchors.top: true
                anchors.left: true
                anchors.right: true
                anchors.bottom: isExpanded

                // Ample headroom for morphing expansions (sharePicker, minimizedApps, etc.)
                implicitHeight: isExpanded ? (screen ? screen.height : 1080) : 380
                color: "transparent"

                // Wayland Input Mask: Clicks outside active capsule pass through in compact mode;
                // when expanded, full window accepts clicks so off-clicks dismiss the popup!
                mask: isExpanded ? null : compactMask

                Region {
                    id: compactMask
                    item: capsule
                    Region {
                        item: (accessoryPill && accessoryPill.visible) ? accessoryPill : null
                    }
                }

                // Off-click backdrop: Clicking anywhere outside the expanded capsule dismisses it
                MouseArea {
                    id: offClickArea
                    anchors.fill: parent
                    visible: islandOverlay.isExpanded
                    z: -1
                    onClicked: {
                        IslandBridge.dismiss();
                    }
                }

                // Centered Morphological Dynamic Island Capsule
                IslandCapsule {
                    id: capsule
                    z: 1
                }

                // Apple Dynamic Island Split Accessory Pill (Secondary Activity Indicator)
                AccessoryPill {
                    id: accessoryPill
                    anchors.left: capsule.right
                    anchors.leftMargin: 8
                    anchors.top: capsule.top
                    anchors.topMargin: Math.max(0, (38 - height) / 2)
                }
            }
        }
    }

    // 2. macOS-Inspired Floating Bottom Dock (Optional & Independent)
    Variants {
        model: Quickshell.screens

        delegate: Component {
            Dock {
                id: floatingDock
                required property var modelData
                screenTarget: modelData
            }
        }
    }

    // 3. Native macOS-Style Window Minimize / Restore Overlay Animator
    Variants {
        model: Quickshell.screens

        delegate: Component {
            WindowMinimizeAnimator {
                required property var modelData
                screenTarget: modelData
            }
        }
    }
}
