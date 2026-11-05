# -*- coding: utf-8 -*-
"""
Finestre dei post-it: una finestra QML (NoteWindow.qml) per ogni nota.
"""

from pathlib import Path
from typing import Any, Dict, Optional

from PyQt6 import sip
from PyQt6.QtCore import QMetaObject, QObject, QUrl
from PyQt6.QtGui import QTextDocument
from PyQt6.QtQml import QQmlComponent, QQmlEngine
from PyQt6.QtQuick import QQuickTextDocument

from ..core import reminders
from ..core.note_model import NoteData
from .text_format import plain_to_html

QML_FILE = Path(__file__).resolve().parent.parent / "qml" / "NoteWindow.qml"


class NoteWindowManager(QObject):
    """Crea, mostra, nasconde e distrugge le finestre delle note"""

    def __init__(self, engine: QQmlEngine, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._component = QQmlComponent(engine, QUrl.fromLocalFile(str(QML_FILE)))
        if self._component.isError():
            errors = "\n".join(e.toString() for e in self._component.errors())
            raise RuntimeError(f"Impossibile caricare {QML_FILE}:\n{errors}")
        self._windows: Dict[str, Any] = {}

    def open(self, note: NoteData) -> Any:
        """Crea la finestra di una nota (visibile solo se la nota lo è)"""
        window = self._component.createWithInitialProperties({
            "noteId": note.id,
            "noteTitle": note.title,
            # Le note delle versioni precedenti hanno solo il testo semplice
            "noteHtml": note.rich_content or plain_to_html(note.content),
            "reminderText": reminders.short_label(note.reminder),
            "noteColor": note.color,
            "keepAbove": note.is_pinned,
            "x": note.x,
            "y": note.y,
            "width": note.width,
            "height": note.height,
        })
        if window is None:
            errors = "\n".join(e.toString() for e in self._component.errors())
            raise RuntimeError(f"Impossibile creare la finestra della nota:\n{errors}")
        self._windows[note.id] = window
        window.setVisible(note.is_visible)
        return window

    def get(self, note_id: str) -> Any:
        return self._windows.get(note_id)

    def show(self, note_id: str, focus: bool = False):
        """Mostra la nota e la porta in primo piano"""
        window = self._windows.get(note_id)
        if window is None:
            return
        window.show()
        window.raise_()
        if focus:
            QMetaObject.invokeMethod(window, "focusBody")
        else:
            window.requestActivate()

    def hide(self, note_id: str):
        window = self._windows.get(note_id)
        if window is not None:
            window.hide()

    def set_property(self, note_id: str, name: str, value: Any):
        window = self._windows.get(note_id)
        if window is not None and window.property(name) != value:
            window.setProperty(name, value)

    def document(self, note_id: str) -> Optional[QTextDocument]:
        """QTextDocument del testo della nota (per la formattazione)"""
        window = self._windows.get(note_id)
        if window is None:
            return None
        body = window.findChild(QObject, "body")
        if body is None:
            return None
        # La proprietà "textDocument" arriva a PyQt come puntatore grezzo:
        # l'oggetto QQuickTextDocument è però figlio del TextEdit
        quick_doc = body.findChild(QQuickTextDocument)
        return quick_doc.textDocument() if quick_doc is not None else None

    def ids(self):
        return list(self._windows)

    def edit_title(self, note_id: str):
        window = self._windows.get(note_id)
        if window is not None:
            QMetaObject.invokeMethod(window, "editTitle")

    def close(self, note_id: str):
        """Distrugge la finestra di una nota eliminata"""
        window = self._windows.pop(note_id, None)
        if window is not None:
            window.hide()
            window.deleteLater()

    def flush_all(self):
        """Salva subito le modifiche pendenti di tutte le note"""
        for window in self._windows.values():
            QMetaObject.invokeMethod(window, "flush")

    def destroy_all(self):
        """Distrugge subito tutte le finestre (prima del motore QML)"""
        for window in self._windows.values():
            sip.delete(window)
        self._windows.clear()
