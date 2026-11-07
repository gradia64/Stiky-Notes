import QtQuick
import QtQuick.Window

// Un post-it: finestra senza bordi del colore della nota.
// - barra superiore: trascina per spostare, doppio clic per il titolo,
//   clic destro (o ⋮) per il menu, ＋ nuova nota, ✕ nasconde la nota
// - barra di formattazione in basso quando la nota è attiva
// - angolo in basso a destra: ridimensiona
// Le modifiche vengono salvate da sole (testo, titolo, posizione e dimensioni).
Window {
    id: note

    required property string noteId
    property string noteTitle: ""
    property string noteHtml: ""
    property color noteColor: "#FFD93D"
    property bool keepAbove: false
    // Testo breve del promemoria ("" = nessun promemoria)
    property string reminderText: ""
    // Titolo temporaneo usato da KWin per riconoscere la finestra
    property string captionOverride: ""

    property string savedHtml: ""

    readonly property color inkColor: "#262626"
    readonly property color headerColor: Qt.darker(noteColor, 1.07)
    readonly property color edgeColor: Qt.darker(noteColor, 1.35)
    readonly property bool showFormatBar: note.active && !titleEdit.visible

    flags: Qt.Window | Qt.FramelessWindowHint
           | (keepAbove ? Qt.WindowStaysOnTopHint : 0)
    title: captionOverride.length > 0 ? captionOverride
                                      : (noteTitle.length > 0 ? noteTitle : "Nota")
    color: noteColor
    minimumWidth: 190
    minimumHeight: 140

    // ===== Salvataggio =====

    // Salva contenuto e titolo se cambiati (chiamata anche da Python all'uscita)
    function flush() {
        saveTimer.stop();
        commitTitle();
        if (body.text !== savedHtml) {
            savedHtml = body.text;
            stikyApp.update_note_content(noteId, body.getText(0, body.length), body.text);
        }
    }

    function editTitle() {
        titleEdit.text = noteTitle;
        titleEdit.visible = true;
        note.requestActivate();
        titleEdit.forceActiveFocus();
        titleEdit.selectAll();
    }

    function commitTitle() {
        if (!titleEdit.visible)
            return;
        titleEdit.visible = false;
        var t = titleEdit.text.trim();
        if (t !== noteTitle) {
            noteTitle = t;
            stikyApp.update_note_title(noteId, t);
        }
    }

    function focusBody() {
        note.requestActivate();
        body.forceActiveFocus();
        body.cursorPosition = body.length;
    }

    // Applica una formattazione alla selezione (o alla parola sotto il cursore)
    function format(action) {
        stikyApp.format_text(noteId, action, body.selectionStart, body.selectionEnd,
                             body.cursorPosition);
        body.forceActiveFocus();
    }

    // Menu del clic destro sul testo: lo costruisce Python, l'azione scelta
    // viene eseguita qui sul TextEdit (così Ctrl+Z continua a funzionare)
    function showTextMenu() {
        var hasSelection = body.selectionStart !== body.selectionEnd;
        var action = stikyApp.show_text_menu(noteId, hasSelection, body.canPaste,
                                             body.canUndo, body.canRedo,
                                             body.length > 0);
        body.forceActiveFocus();
        switch (action) {
        case "undo": body.undo(); break;
        case "redo": body.redo(); break;
        case "cut": body.cut(); break;
        case "copy": body.copy(); break;
        case "paste": body.paste(); break;
        case "delete": body.remove(body.selectionStart, body.selectionEnd); break;
        case "selectAll": body.selectAll(); break;
        case "": break;
        default: note.format(action);
        }
    }

    Timer {
        id: saveTimer
        interval: 500
        onTriggered: note.flush()
    }

    Timer {
        id: geometryTimer
        interval: 600
        onTriggered: stikyApp.update_note_geometry(note.noteId, note.x, note.y,
                                                   note.width, note.height)
    }

    onXChanged: geometryTimer.restart()
    onYChanged: geometryTimer.restart()
    onWidthChanged: geometryTimer.restart()
    onHeightChanged: geometryTimer.restart()

    // Quando la nota perde il focus si salva subito
    onActiveChanged: if (!active) flush()

    // Alt+F4 / chiusura dal window manager: la nota viene nascosta, non eliminata
    onClosing: {
        flush();
        stikyApp.hide_note(noteId);
    }

    Component.onCompleted: {
        body.text = noteHtml;
        savedHtml = body.text;
    }

    Shortcut { sequence: "Ctrl+N"; onActivated: stikyApp.create_new_note() }
    Shortcut { sequence: "Ctrl+B"; onActivated: note.format("bold") }
    Shortcut { sequence: "Ctrl+I"; onActivated: note.format("italic") }
    Shortcut { sequence: "Ctrl+U"; onActivated: note.format("underline") }

    // ===== Barra superiore =====

    Rectangle {
        id: header
        anchors { left: parent.left; right: parent.right; top: parent.top }
        height: 30
        color: note.headerColor

        MouseArea {
            id: dragArea
            anchors.fill: parent
            acceptedButtons: Qt.LeftButton | Qt.RightButton
            property point pressPos

            // Lo spostamento parte solo dopo qualche pixel: così clic e doppio
            // clic restano disponibili (startSystemMove cede il puntatore al WM)
            onPressed: (mouse) => { pressPos = Qt.point(mouse.x, mouse.y) }
            onPositionChanged: (mouse) => {
                if ((mouse.buttons & Qt.LeftButton)
                        && Math.abs(mouse.x - pressPos.x) + Math.abs(mouse.y - pressPos.y) > 4)
                    note.startSystemMove();
            }
            onClicked: (mouse) => {
                if (mouse.button === Qt.RightButton)
                    stikyApp.show_note_menu(note.noteId);
            }
            onDoubleClicked: (mouse) => {
                if (mouse.button === Qt.LeftButton)
                    note.editTitle();
            }
        }

        Text {
            anchors { left: parent.left; leftMargin: 9; right: reminderBadge.left; rightMargin: 4
                      verticalCenter: parent.verticalCenter }
            visible: !titleEdit.visible
            text: note.noteTitle
            color: note.inkColor
            font.pixelSize: 13
            font.bold: true
            elide: Text.ElideRight
        }

        TextInput {
            id: titleEdit
            visible: false
            anchors { left: parent.left; leftMargin: 9; right: reminderBadge.left; rightMargin: 4
                      verticalCenter: parent.verticalCenter }
            color: note.inkColor
            font.pixelSize: 13
            font.bold: true
            selectByMouse: true
            clip: true
            onAccepted: { note.commitTitle(); note.focusBody(); }
            onActiveFocusChanged: if (!activeFocus) note.commitTitle()
            Keys.onEscapePressed: { visible = false; note.focusBody(); }
        }

        // Promemoria impostato: ⏰ + data/ora, clic per modificarlo
        Rectangle {
            id: reminderBadge
            anchors { right: buttons.left; rightMargin: 2; verticalCenter: parent.verticalCenter }
            visible: note.reminderText.length > 0
            width: visible ? reminderLabel.implicitWidth + 10 : 0
            height: 20
            radius: 4
            color: reminderMouse.containsMouse ? Qt.rgba(0, 0, 0, 0.09) : "transparent"

            Text {
                id: reminderLabel
                anchors.centerIn: parent
                text: "⏰ " + note.reminderText
                color: note.inkColor
                font.pixelSize: 11
            }

            MouseArea {
                id: reminderMouse
                anchors.fill: parent
                hoverEnabled: true
                onClicked: stikyApp.edit_reminder(note.noteId)
            }

            Accessible.role: Accessible.Button
            Accessible.name: "Promemoria " + note.reminderText
        }

        Row {
            id: buttons
            anchors { right: parent.right; rightMargin: 3; verticalCenter: parent.verticalCenter }
            spacing: 1

            HeaderButton {
                glyph: "+"
                tip: "Nuova nota"
                onClicked: stikyApp.create_new_note()
            }
            HeaderButton {
                glyph: "⋮"
                tip: "Menu"
                onClicked: stikyApp.show_note_menu(note.noteId)
            }
            HeaderButton {
                glyph: "✕"
                tip: "Nascondi"
                onClicked: { note.flush(); stikyApp.hide_note(note.noteId); }
            }
        }
    }

    // ===== Testo della nota =====

    Flickable {
        id: flick
        anchors { left: parent.left; right: parent.right; top: header.bottom
                  bottom: note.showFormatBar ? formatBar.top : parent.bottom
                  margins: 9; bottomMargin: note.showFormatBar ? 2 : 14 }
        contentWidth: width
        contentHeight: body.height
        clip: true
        boundsBehavior: Flickable.StopAtBounds

        function ensureVisible(r) {
            if (contentY >= r.y)
                contentY = r.y;
            else if (contentY + height <= r.y + r.height)
                contentY = r.y + r.height - height;
        }

        TextEdit {
            id: body
            objectName: "body"
            width: flick.width
            height: Math.max(contentHeight, flick.height)
            textFormat: TextEdit.RichText
            wrapMode: TextEdit.Wrap
            color: note.inkColor
            selectionColor: Qt.darker(note.noteColor, 1.6)
            selectedTextColor: "#FFFFFF"
            font.pixelSize: 14
            selectByMouse: true
            persistentSelection: true
            onTextChanged: if (text !== note.savedHtml) saveTimer.restart()
            onCursorRectangleChanged: flick.ensureVisible(cursorRectangle)

            // Clic destro: menu Taglia/Copia/Incolla… (il clic sinistro passa al testo)
            MouseArea {
                anchors.fill: parent
                acceptedButtons: Qt.RightButton
                cursorShape: Qt.IBeamShape
                onPressed: function (mouse) {
                    note.requestActivate();
                    body.forceActiveFocus();
                    // Fuori dalla selezione: sposta il cursore dove si è cliccato
                    var pos = body.positionAt(mouse.x, mouse.y);
                    var a = Math.min(body.selectionStart, body.selectionEnd);
                    var b = Math.max(body.selectionStart, body.selectionEnd);
                    if (a === b || pos < a || pos > b)
                        body.cursorPosition = pos;
                }
                onClicked: note.showTextMenu()
            }

            Text {
                visible: body.length === 0 && !body.activeFocus
                text: "Scrivi qui…"
                color: Qt.darker(note.noteColor, 1.6)
                font: body.font
            }
        }
    }

    // ===== Barra di formattazione (solo con la nota attiva) =====

    Row {
        id: formatBar
        visible: note.showFormatBar
        anchors { left: parent.left; leftMargin: 5; bottom: parent.bottom; bottomMargin: 3 }
        spacing: 1

        readonly property font current: body.cursorSelection.font

        HeaderButton {
            glyph: "B"; tip: "Grassetto (Ctrl+B)"
            font.bold: true; font.pixelSize: 13
            checked: formatBar.current.bold
            onClicked: note.format("bold")
        }
        HeaderButton {
            glyph: "I"; tip: "Corsivo (Ctrl+I)"
            font.italic: true; font.pixelSize: 13; font.family: "serif"
            checked: formatBar.current.italic
            onClicked: note.format("italic")
        }
        HeaderButton {
            glyph: "U"; tip: "Sottolineato (Ctrl+U)"
            font.underline: true; font.pixelSize: 13
            checked: formatBar.current.underline
            onClicked: note.format("underline")
        }
        HeaderButton {
            glyph: "S"; tip: "Barrato"
            font.strikeout: true; font.pixelSize: 13
            checked: formatBar.current.strikeout
            onClicked: note.format("strike")
        }
        HeaderButton {
            glyph: "•"; tip: "Elenco puntato"
            onClicked: note.format("bullet")
        }
        HeaderButton {
            glyph: "1."; tip: "Elenco numerato"
            font.pixelSize: 12
            onClicked: note.format("numbered")
        }
        HeaderButton {
            glyph: "⌫"; tip: "Rimuovi formattazione"
            font.pixelSize: 13
            onClicked: note.format("clear")
        }
    }

    // ===== Maniglia di ridimensionamento =====

    Item {
        width: 16
        height: 16
        anchors { right: parent.right; bottom: parent.bottom }

        Canvas {
            anchors.fill: parent
            onPaint: {
                var ctx = getContext("2d");
                ctx.strokeStyle = note.edgeColor;
                ctx.lineWidth = 1;
                for (var i = 4; i <= 12; i += 4) {
                    ctx.beginPath();
                    ctx.moveTo(width - i, height - 2);
                    ctx.lineTo(width - 2, height - i);
                    ctx.stroke();
                }
            }
        }

        MouseArea {
            anchors.fill: parent
            cursorShape: Qt.SizeFDiagCursor
            onPressed: note.startSystemResize(Qt.RightEdge | Qt.BottomEdge)
        }
    }

    // Bordo sottile per staccare la nota dallo sfondo
    Rectangle {
        anchors.fill: parent
        color: "transparent"
        border.color: note.edgeColor
        border.width: 1
    }
}
