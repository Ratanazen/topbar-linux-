import Quickshell
import Quickshell.Wayland
import QtQuick
import "components"
import "services"
import "themes"
import "dock"

ShellRoot {
    id: root

    // 1. Dynamic Island Top Layer-Shell Overlay
    Variants {
        model: Quickshell.screens

        delegate: Component {
            PanelWindow {
                id: islandOverlay
                required property var modelData
                screen: modelData

                // Layer Shell Protocol Properties
                WlrLayershell.layer: WlrLayer.Top
                WlrLayershell.namespace: "ratana-island"
                WlrLayershell.keyboardFocus: (IslandBridge.userExpanded || IslandBridge.quickActionsOpen || IslandBridge.settingsOpen) ? WlrKeyboardFocus.OnDemand : WlrKeyboardFocus.None
                WlrLayershell.exclusionMode: ExclusionMode.Ignore
                exclusionMode: ExclusionMode.Ignore

                // Anchor to top edge with full width
                anchors.top: true
                anchors.left: true
                anchors.right: true

                // Ample headroom for morphing expansions
                implicitHeight: 260
                color: "transparent"

                // Wayland Input Mask: Clicks outside the active capsule pass through!
                mask: Region {
                    item: capsule
                }

                // Centered Morphological Dynamic Island Capsule
                IslandCapsule {
                    id: capsule
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
