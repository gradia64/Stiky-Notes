# -*- coding: utf-8 -*-
"""
Istanza singola dell'applicazione tramite D-Bus di sessione.

La prima istanza registra il nome ``org.kde.StikyNotes`` sul bus di sessione
ed esporta un piccolo oggetto con i metodi ``NewNote`` e ``ShowAll``
(più ``PointerPosition``, con cui KWin risponde a ``kwin_pointer.request``).
Un secondo avvio (es. le azioni "Nuova nota"/"Mostra tutte le note" del file
.desktop) non crea un altro processo con un'altra icona nel vassoio e un
modello dati concorrente: inoltra la richiesta all'istanza già attiva ed esce.

Il nome coincide con il file di attivazione D-Bus installato dal pacchetto
(/usr/share/dbus-1/services/org.kde.StikyNotes.service).
"""

from typing import Optional

from PyQt6.QtCore import QObject, pyqtClassInfo, pyqtSignal, pyqtSlot
from PyQt6.QtDBus import QDBusConnection, QDBusInterface, QDBusMessage

DBUS_SERVICE = "org.kde.StikyNotes"
DBUS_PATH = "/org/kde/StikyNotes"
DBUS_INTERFACE = "org.kde.StikyNotes"


@pyqtClassInfo("D-Bus Interface", DBUS_INTERFACE)
class SingleInstanceService(QObject):
    """Oggetto esportato su D-Bus dall'istanza principale."""

    new_note_requested = pyqtSignal()
    show_all_requested = pyqtSignal()
    # x, y del puntatore e geometria del desktop, nelle coordinate di KWin
    pointer_reported = pyqtSignal(int, int, int, int, int, int)

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._registered = False

    def register(self) -> bool:
        """Registra il servizio. Restituisce False se un'altra istanza lo possiede già."""
        bus = QDBusConnection.sessionBus()
        if not bus.isConnected():
            # Nessun bus di sessione: si procede senza controllo di istanza singola
            return True
        if not bus.registerService(DBUS_SERVICE):
            return False
        bus.registerObject(
            DBUS_PATH, self, QDBusConnection.RegisterOption.ExportAllSlots
        )
        self._registered = True
        return True

    def unregister(self):
        """Rilascia il nome sul bus (chiamata in fase di chiusura)."""
        if not self._registered:
            return
        bus = QDBusConnection.sessionBus()
        bus.unregisterObject(DBUS_PATH)
        bus.unregisterService(DBUS_SERVICE)
        self._registered = False

    @pyqtSlot()
    def NewNote(self):
        self.new_note_requested.emit()

    @pyqtSlot()
    def ShowAll(self):
        self.show_all_requested.emit()

    @pyqtSlot(int, int, int, int, int, int)
    def PointerPosition(self, x: int, y: int, area_x: int, area_y: int,
                        area_width: int, area_height: int):
        self.pointer_reported.emit(x, y, area_x, area_y, area_width, area_height)


def forward_to_running_instance(method: str) -> bool:
    """Invoca ``method`` sull'istanza già in esecuzione. True se la chiamata riesce."""
    bus = QDBusConnection.sessionBus()
    if not bus.isConnected():
        return False
    iface = QDBusInterface(DBUS_SERVICE, DBUS_PATH, DBUS_INTERFACE, bus)
    if not iface.isValid():
        return False
    reply = iface.call(method)
    return reply.type() != QDBusMessage.MessageType.ErrorMessage
