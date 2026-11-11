# -*- coding: utf-8 -*-
"""
Icona di Stiky-notes nell'area di notifica (system tray).

- Clic: elenco delle note, per richiamarne una (più nuova nota e
  mostra/nascondi tutte)
- Clic centrale: nuova nota
- Clic destro: nuova nota, elenco delle note, mostra/nascondi tutte, avvio
  automatico, informazioni, esci
"""

import os
import sys
from pathlib import Path
from typing import List, Optional, Tuple

from PyQt6.QtCore import QObject, QPoint, QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QColor, QGuiApplication, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from ..platform import autostart

ICON_DIR = Path(__file__).resolve().parent.parent / "icons"


def app_icon() -> QIcon:
    """Icona dell'app: quella del tema, oppure gli SVG inclusi nel pacchetto
    (variante semplificata per le dimensioni piccole)."""
    bundled = QIcon()
    for size in (16, 22, 24):
        bundled.addFile(str(ICON_DIR / "stiky-notes-small.svg"), QSize(size, size))
    for size in (32, 48, 64, 128, 256):
        bundled.addFile(str(ICON_DIR / "stiky-notes.svg"), QSize(size, size))
    return QIcon.fromTheme("stiky-notes", bundled)

# Sotto XWayland un clic su una finestra Wayland non chiude il menu del clic
# sinistro (l'applicazione non lo vede): il menu si chiude da solo se il
# puntatore non ci sta sopra per questo tempo.
MENU_CHECK_MS = 500
MENU_IDLE_CHECKS = 8

# (id, etichetta, colore) di ogni nota mostrata nel menu
NoteEntry = Tuple[str, str, str]


def color_icon(color: str, size: int = 16, square: bool = False) -> QIcon:
    """Icona tinta unita (cerchio o quadrato) del colore indicato"""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor(color))
    painter.setPen(QColor(color).darker(140))
    if square:
        painter.drawRoundedRect(2, 2, size - 4, size - 4, 2, 2)
    else:
        painter.drawEllipse(2, 2, size - 4, size - 4)
    painter.end()
    return QIcon(pixmap)


class TrayManager(QObject):
    """Gestore dell'area di notifica per Stiky-notes"""

    new_note_requested = pyqtSignal()
    show_all_requested = pyqtSignal()
    hide_all_requested = pyqtSignal()
    note_activated = pyqtSignal(str)
    notes_menu_requested = pyqtSignal()
    about_requested = pyqtSignal()
    message_clicked = pyqtSignal()

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._tray_icon = QSystemTrayIcon()
        self._tray_icon.setToolTip("Stiky-notes")
        self._tray_icon.setIcon(app_icon())
        self._tray_icon.activated.connect(self._on_tray_icon_activated)
        self._tray_icon.messageClicked.connect(self.message_clicked.emit)

        self._notes: List[NoteEntry] = []
        self._menu = QMenu()
        self._notes_menu = QMenu("Note")
        self._build_menu()

        # Menu del clic sinistro, ricreato a ogni apertura
        self._click_menu = QMenu()
        self._idle_checks = 0
        self._menu_watchdog = QTimer(self)
        self._menu_watchdog.setInterval(MENU_CHECK_MS)
        self._menu_watchdog.timeout.connect(self._check_click_menu)
        self._click_menu.aboutToHide.connect(self._menu_watchdog.stop)

    def _build_menu(self):
        """Crea il menu contestuale dell'icona"""
        new_note_action = QAction("Nuova nota", self)
        new_note_action.triggered.connect(self.new_note_requested.emit)
        self._menu.addAction(new_note_action)

        self._menu.addSeparator()
        self._menu.addMenu(self._notes_menu)

        show_all_action = QAction("Mostra tutte le note", self)
        show_all_action.triggered.connect(self.show_all_requested.emit)
        self._menu.addAction(show_all_action)

        hide_all_action = QAction("Nascondi tutte le note", self)
        hide_all_action.triggered.connect(self.hide_all_requested.emit)
        self._menu.addAction(hide_all_action)

        self._menu.addSeparator()

        # Stato reale letto dai file di autostart XDG
        startup_action = QAction("Avvio automatico", self)
        startup_action.setCheckable(True)
        startup_action.setChecked(autostart.is_enabled())
        startup_action.toggled.connect(self._on_startup_toggled)
        self._menu.addAction(startup_action)

        self._menu.addSeparator()

        about_action = QAction(
            QIcon.fromTheme("help-about"), "Informazioni su Stiky-notes", self)
        about_action.triggered.connect(self.about_requested.emit)
        self._menu.addAction(about_action)

        exit_action = QAction("Esci", self)
        exit_action.triggered.connect(QApplication.quit)
        self._menu.addAction(exit_action)

        self._rebuild_notes_menu()

        # Su KDE Plasma il menu viene esportato via DBusMenu e mostrato
        # nativamente al click destro; su X11 lo mostra Qt stesso.
        self._tray_icon.setContextMenu(self._menu)

    def set_notes(self, notes: List[NoteEntry]):
        """Aggiorna l'elenco delle note nel menu (solo se è cambiato)"""
        if notes == self._notes:
            return
        self._notes = list(notes)
        self._rebuild_notes_menu()

    def _rebuild_notes_menu(self):
        self._notes_menu.clear()
        self._add_note_actions(self._notes_menu)

    def _add_note_actions(self, menu: QMenu):
        """Una voce per nota: sceglierla la richiama in primo piano"""
        if not self._notes:
            empty = menu.addAction("Nessuna nota")
            empty.setEnabled(False)
            return
        for note_id, label, color in self._notes:
            action = menu.addAction(color_icon(color, square=True), label)
            action.triggered.connect(
                lambda _checked=False, nid=note_id: self.note_activated.emit(nid)
            )

    def popup_notes_menu(self, pointer: QPoint):
        """Apre accanto al puntatore l'elenco delle note (clic sull'icona)"""
        menu = self._click_menu
        menu.clear()
        self._add_note_actions(menu)
        menu.addSeparator()
        menu.addAction("Nuova nota").triggered.connect(self.new_note_requested.emit)
        if self._notes:
            menu.addAction("Mostra tutte le note").triggered.connect(
                self.show_all_requested.emit)
            menu.addAction("Nascondi tutte le note").triggered.connect(
                self.hide_all_requested.emit)
        menu.addSeparator()
        menu.addAction(QIcon.fromTheme("help-about"), "Informazioni su Stiky-notes"
                       ).triggered.connect(self.about_requested.emit)

        menu.popup(self._menu_position(pointer, menu.sizeHint()))
        if os.environ.get("XDG_SESSION_TYPE") == "wayland":
            self._idle_checks = 0
            self._menu_watchdog.start()

    @staticmethod
    def _menu_position(pointer: QPoint, size: QSize) -> QPoint:
        """Angolo del menu: sopra il puntatore se il vassoio è in basso,
        sotto se è in alto, sempre dentro lo schermo."""
        screen = QGuiApplication.screenAt(pointer) or QGuiApplication.primaryScreen()
        area = screen.geometry()
        x = pointer.x() - size.width() // 2
        x = max(area.left(), min(x, area.right() - size.width()))
        if pointer.y() > area.center().y():
            y = pointer.y() - size.height()
        else:
            y = pointer.y()
        y = max(area.top(), min(y, area.bottom() - size.height()))
        return QPoint(x, y)

    def _check_click_menu(self):
        """Chiude il menu del clic sinistro rimasto aperto senza puntatore sopra"""
        if self._click_menu.underMouse():
            self._idle_checks = 0
            return
        self._idle_checks += 1
        if self._idle_checks >= MENU_IDLE_CHECKS:
            self._click_menu.close()

    def _on_tray_icon_activated(self, reason):
        """Clic sull'icona.

        Con StatusNotifierItem (KDE Plasma/Wayland) il click destro è gestito
        nativamente dal menu registrato con setContextMenu() e il motivo
        "Context" non arriva mai all'applicazione; il protocollo inoltre non
        invia mai "DoubleClick", ogni click semplice arriva come "Trigger".
        """
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            # Un secondo clic sull'icona richiude l'elenco
            if self._click_menu.isVisible():
                self._click_menu.close()
            else:
                self.notes_menu_requested.emit()
        elif reason == QSystemTrayIcon.ActivationReason.MiddleClick:
            self.new_note_requested.emit()

    def _on_startup_toggled(self, enabled: bool):
        """Attiva/disattiva l'avvio automatico (file XDG autostart)"""
        if not autostart.set_enabled(enabled):
            print("[TrayManager] Impossibile modificare l'avvio automatico", file=sys.stderr)

    def notify(self, title: str, message: str):
        """Notifica di sistema (su Plasma passa dal servizio delle notifiche)"""
        self._tray_icon.showMessage(
            title, message, QSystemTrayIcon.MessageIcon.Information, 0
        )

    def show_tray_icon(self):
        """Mostra l'icona nell'area di notifica"""
        self._tray_icon.show()

    def cleanup(self):
        """Nasconde l'icona in fase di chiusura"""
        self._click_menu.close()
        self._tray_icon.hide()
