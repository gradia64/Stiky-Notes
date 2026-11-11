# -*- coding: utf-8 -*-
"""
Posizione reale del puntatore, chiesta a KWin.

Sotto XWayland un'applicazione conosce la posizione del puntatore solo
finché questo è sopra una finestra X11: sul pannello di Plasma (una
superficie Wayland) ``QCursor.pos()`` restituisce l'ultima posizione nota,
anche su un altro schermo. Per aprire un menu accanto all'icona del vassoio
si chiede quindi la posizione a KWin con uno script, che risponde chiamando
il metodo D-Bus ``PointerPosition`` dell'istanza (vedi ``single_instance``).
"""

from PyQt6.QtCore import QPoint, QRect

from . import kwin_desktops
from .single_instance import DBUS_INTERFACE, DBUS_PATH, DBUS_SERVICE

SCRIPT_NAME = "stiky-notes-pointer"

_SCRIPT = """
const p = workspace.cursorPos;
const g = workspace.virtualScreenGeometry;
callDBus("%s", "%s", "%s", "PointerPosition",
         Math.round(p.x), Math.round(p.y),
         Math.round(g.x), Math.round(g.y), Math.round(g.width), Math.round(g.height));
""" % (DBUS_SERVICE, DBUS_PATH, DBUS_INTERFACE)


def request() -> bool:
    """Chiede a KWin la posizione del puntatore. True se lo script è partito:
    la risposta arriva dal segnale ``SingleInstanceService.pointer_reported``."""
    return kwin_desktops.run_script(_SCRIPT, SCRIPT_NAME)


def to_local(x: int, y: int, kwin_area: QRect, local_area: QRect) -> QPoint:
    """Converte un punto dalle coordinate di KWin a quelle dell'applicazione.

    Le due aree sono lo stesso desktop (tutti gli schermi) visto da KWin e da
    Qt: con XWayland in scala le dimensioni differiscono di un fattore fisso.
    """
    if kwin_area.width() <= 0 or kwin_area.height() <= 0:
        return QPoint(x, y)
    return QPoint(
        local_area.x() + round((x - kwin_area.x()) * local_area.width() / kwin_area.width()),
        local_area.y() + round((y - kwin_area.y()) * local_area.height() / kwin_area.height()),
    )
