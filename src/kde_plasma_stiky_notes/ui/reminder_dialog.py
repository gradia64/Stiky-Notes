# -*- coding: utf-8 -*-
"""Finestra di dialogo per impostare o rimuovere il promemoria di una nota."""

from datetime import datetime
from typing import Optional, Tuple

from PyQt6.QtCore import QDate, QDateTime, Qt, QTime
from PyQt6.QtWidgets import (
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QTimeEdit,
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
    when = when.astimezone().replace(tzinfo=None)

    # Data e ora in due campi separati. Niente minimo sui campi: Qt lo applica
    # anche mentre si digita e rifiuterebbe le cifre intermedie (es. il "2" di
    # "23"); la data passata viene invece segnalata e blocca solo "OK".
    date_edit = QDateEdit(QDate(when.year, when.month, when.day))
    date_edit.setCalendarPopup(True)
    date_edit.setDisplayFormat("dddd d MMMM yyyy")
    time_edit = QTimeEdit(QTime(when.hour, when.minute))
    time_edit.setDisplayFormat("HH:mm")
    time_edit.setWrapping(True)
    row = QHBoxLayout()
    row.addWidget(date_edit, 1)
    row.addWidget(QLabel("alle"))
    row.addWidget(time_edit)
    layout.addLayout(row)

    warning = QLabel("L'orario scelto è già passato.")
    warning.setStyleSheet("color: #c0392b;")
    layout.addWidget(warning)

    buttons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
    )
    ok_button = buttons.button(QDialogButtonBox.StandardButton.Ok)

    def chosen_datetime() -> QDateTime:
        return QDateTime(date_edit.date(), time_edit.time())

    def validate(*_):
        past = chosen_datetime() <= QDateTime.currentDateTime()
        warning.setVisible(past)
        ok_button.setEnabled(not past)

    date_edit.dateChanged.connect(validate)
    time_edit.timeChanged.connect(validate)
    validate()
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
    chosen = chosen_datetime().toPyDateTime().astimezone()
    return SET, chosen
