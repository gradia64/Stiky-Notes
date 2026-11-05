# -*- coding: utf-8 -*-
"""Finestra di dialogo per impostare o rimuovere il promemoria di una nota."""

from datetime import datetime
from typing import Optional, Tuple

from PyQt6.QtCore import QDateTime, Qt
from PyQt6.QtWidgets import (
    QDateTimeEdit,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QVBoxLayout,
)

from ..core import reminders

# Esiti della finestra
CANCEL = "cancel"
SET = "set"
REMOVE = "remove"


def ask_reminder(note_label: str, current: Optional[str]) -> Tuple[str, Optional[datetime]]:
    """Chiede data e ora del promemoria. Restituisce (esito, data/ora)."""
    dialog = QDialog()
    dialog.setWindowTitle("Promemoria")
    dialog.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)

    layout = QVBoxLayout(dialog)
    layout.addWidget(QLabel(f"Avvisami per la nota «{note_label}»:"))

    when = reminders.parse(current) or reminders.default_time()
    edit = QDateTimeEdit(QDateTime(when.replace(tzinfo=None)))
    edit.setCalendarPopup(True)
    edit.setDisplayFormat("dddd d MMMM yyyy  HH:mm")
    edit.setMinimumDateTime(QDateTime.currentDateTime().addSecs(-60))
    layout.addWidget(edit)

    buttons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
    )
    remove_button = None
    if current:
        remove_button = buttons.addButton("Rimuovi promemoria",
                                          QDialogButtonBox.ButtonRole.DestructiveRole)
    layout.addWidget(buttons)

    result = {"action": CANCEL}
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    if remove_button is not None:
        def on_remove():
            result["action"] = REMOVE
            dialog.accept()
        remove_button.clicked.connect(on_remove)

    if dialog.exec() != QDialog.DialogCode.Accepted:
        return CANCEL, None
    if result["action"] == REMOVE:
        return REMOVE, None
    chosen = edit.dateTime().toPyDateTime().astimezone()
    return SET, chosen
