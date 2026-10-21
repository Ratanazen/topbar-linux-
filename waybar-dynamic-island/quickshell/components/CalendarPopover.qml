import QtQuick
import "../services"
import "../themes"

Rectangle {
    id: root
    width: 280
    height: 310
    radius: 14
    color: Theme.background
    border.color: Theme.border
    border.width: 1

    property var currentDate: new Date()
    property int displayYear: currentDate.getFullYear()
    property int displayMonth: currentDate.getMonth() // 0-11

    readonly property var monthNames: [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]

    function daysInMonth(y, m) {
        return new Date(y, m + 1, 0).getDate();
    }

    function firstDayOffset(y, m) {
        return new Date(y, m, 1).getDay(); // 0 = Sunday
    }

    Column {
        anchors.fill: parent
        anchors.margins: 14
        spacing: 10

        // -------------------------------------------------------------
        // Month / Year Navigation Header
        // -------------------------------------------------------------
        Item {
            width: parent.width
            height: 24

            Text {
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                text: monthNames[displayMonth] + " " + displayYear
                color: Theme.textPrimary
                font.pixelSize: 13
                font.bold: true
                font.family: Theme.fontFamily
            }

            Row {
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                spacing: 6

                // Prev Month
                Rectangle {
                    width: 22
                    height: 22
                    radius: 11
                    color: prevHover.hovered ? Qt.rgba(1, 1, 1, 0.18) : Qt.rgba(1, 1, 1, 0.08)

                    Text {
                        anchors.centerIn: parent
                        text: "‹"
                        color: Theme.textPrimary
                        font.pixelSize: 14
                        font.bold: true
                    }
                    HoverHandler { id: prevHover }
                    TapHandler {
                        onTapped: {
                            if (displayMonth === 0) {
                                displayMonth = 11;
                                displayYear -= 1;
                            } else {
                                displayMonth -= 1;
                            }
                        }
                    }
                }

                // Next Month
                Rectangle {
                    width: 22
                    height: 22
                    radius: 11
                    color: nextHover.hovered ? Qt.rgba(1, 1, 1, 0.18) : Qt.rgba(1, 1, 1, 0.08)

                    Text {
                        anchors.centerIn: parent
                        text: "›"
                        color: Theme.textPrimary
                        font.pixelSize: 14
                        font.bold: true
                    }
                    HoverHandler { id: nextHover }
                    TapHandler {
                        onTapped: {
                            if (displayMonth === 11) {
                                displayMonth = 0;
                                displayYear += 1;
                            } else {
                                displayMonth += 1;
                            }
                        }
                    }
                }

                // Close Button
                Rectangle {
                    width: 22
                    height: 22
                    radius: 11
                    color: closeHover.hovered ? Qt.rgba(1, 1, 1, 0.20) : Qt.rgba(1, 1, 1, 0.08)

                    Text {
                        anchors.centerIn: parent
                        text: "✕"
                        color: Theme.textSecondary
                        font.pixelSize: 10
                    }
                    HoverHandler { id: closeHover }
                    TapHandler { onTapped: IslandBridge.dismiss() }
                }
            }
        }

        // -------------------------------------------------------------
        // Day-of-Week Column Labels
        // -------------------------------------------------------------
        Row {
            width: parent.width
            spacing: 0

            Repeater {
                model: ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"]
                delegate: Item {
                    width: root.width / 7 - 4
                    height: 18

                    Text {
                        anchors.centerIn: parent
                        text: modelData
                        color: Theme.textSecondary
                        font.pixelSize: 10
                        font.bold: true
                    }
                }
            }
        }

        // -------------------------------------------------------------
        // Days Grid (6 rows x 7 days)
        // -------------------------------------------------------------
        Grid {
            columns: 7
            spacing: 2
            width: parent.width

            Repeater {
                model: 42 // 6 weeks

                delegate: Item {
                    id: dayCell
                    width: (root.width - 28 - 12) / 7
                    height: 24

                    readonly property int offset: firstDayOffset(displayYear, displayMonth)
                    readonly property int totalDays: daysInMonth(displayYear, displayMonth)
                    readonly property int dayNum: index - offset + 1
                    readonly property bool isCurrentMonth: dayNum >= 1 && dayNum <= totalDays
                    readonly property bool isToday: isCurrentMonth &&
                                                    dayNum === currentDate.getDate() &&
                                                    displayMonth === currentDate.getMonth() &&
                                                    displayYear === currentDate.getFullYear()

                    Rectangle {
                        anchors.centerIn: parent
                        width: 22
                        height: 22
                        radius: 11
                        color: isToday ? Theme.accent : (dayHover.hovered && isCurrentMonth ? Qt.rgba(1, 1, 1, 0.12) : "transparent")

                        Text {
                            anchors.centerIn: parent
                            text: isCurrentMonth ? dayNum : ""
                            color: isToday ? "#ffffff" : (isCurrentMonth ? Theme.textPrimary : "transparent")
                            font.pixelSize: 11
                            font.bold: isToday
                        }
                    }

                    HoverHandler { id: dayHover }
                }
            }
        }

        // -------------------------------------------------------------
        // Footer: Today Shortcut
        // -------------------------------------------------------------
        Rectangle {
            width: parent.width
            height: 1
            color: Qt.rgba(1, 1, 1, 0.08)
        }

        Item {
            width: parent.width
            height: 20

            Text {
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                text: Qt.formatDateTime(new Date(), "dddd, MMMM d")
                color: Theme.textSecondary
                font.pixelSize: 10
            }

            Rectangle {
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                width: todayLabel.implicitWidth + 12
                height: 18
                radius: 9
                color: todayHover.hovered ? Qt.rgba(1, 1, 1, 0.18) : Qt.rgba(1, 1, 1, 0.08)

                Text {
                    id: todayLabel
                    anchors.centerIn: parent
                    text: "Today"
                    color: Theme.accent
                    font.pixelSize: 9
                    font.bold: true
                }

                HoverHandler { id: todayHover }
                TapHandler {
                    onTapped: {
                        displayYear = currentDate.getFullYear();
                        displayMonth = currentDate.getMonth();
                    }
                }
            }
        }
    }
}
