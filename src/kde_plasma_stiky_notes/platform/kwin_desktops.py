# -*- coding: utf-8 -*-
"""
Desktop virtuali tramite KWin (D-Bus e script KWin).

Un'applicazione non può spostare da sola le proprie finestre tra i desktop
virtuali: su Wayland non esiste un protocollo per farlo e, per le finestre
XWayland, KWin ignora la richiesta EWMH _NET_WM_DESKTOP. KWin però esegue
script JavaScript caricati via D-Bus, che possono impostare ``desktops`` e
``onAllDesktops`` di qualsiasi finestra.

La finestra viene identificata dal titolo: chi chiama assegna per un istante
alla nota un titolo univoco (vedi ``token_for``), esegue ``apply`` e poi
ripristina il titolo.
"""

import json
import os
import tempfile
from typing import List, Sequence, Tuple

from PyQt6.QtDBus import QDBusConnection, QDBusInterface, QDBusMessage

KWIN_SERVICE = "org.kde.KWin"
SCRIPT_NAME = "stiky-notes-desktops"

# (titolo temporaneo della finestra, su tutti i desktop, indice del desktop)
DesktopRequest = Tuple[str, bool, int]

_SCRIPT = """
const requests = %s;
for (const w of workspace.windowList()) {
    for (const r of requests) {
        if (w.caption !== r.token)
            continue;
        if (r.all) {
            w.onAllDesktops = true;
        } else {
            const d = workspace.desktops[r.index];
            if (d) {
                w.onAllDesktops = false;
                w.desktops = [d];
            }
        }
    }
}
"""


def token_for(note_id: str) -> str:
    """Titolo temporaneo univoco per riconoscere la finestra di una nota"""
    return f"stiky-notes:{note_id}"


def _bus() -> QDBusConnection:
    return QDBusConnection.sessionBus()


def available() -> bool:
    """True se KWin è raggiungibile su D-Bus con il supporto agli script"""
    bus = _bus()
    if not bus.isConnected():
        return False
    return QDBusInterface(KWIN_SERVICE, "/Scripting", "org.kde.kwin.Scripting", bus).isValid()


def desktop_names() -> List[str]:
    """Nomi dei desktop virtuali, nell'ordine (vuoto se KWin non risponde)"""
    msg = QDBusMessage.createMethodCall(
        KWIN_SERVICE, "/VirtualDesktopManager",
        "org.freedesktop.DBus.Properties", "Get",
    )
    msg.setArguments(["org.kde.KWin.VirtualDesktopManager", "desktops"])
    reply = _bus().call(msg)
    if reply.type() == QDBusMessage.MessageType.ErrorMessage or not reply.arguments():
        return []
    try:
        # a(uss): (posizione, id, nome)
        desktops = sorted(reply.arguments()[0], key=lambda d: d[0])
        return [str(d[2]) for d in desktops]
    except (TypeError, IndexError):
        return []


def apply(requests: Sequence[DesktopRequest]) -> bool:
    """Esegue uno script KWin che sposta le finestre indicate. True se eseguito."""
    if not requests:
        return True
    bus = _bus()
    scripting = QDBusInterface(KWIN_SERVICE, "/Scripting", "org.kde.kwin.Scripting", bus)
    if not scripting.isValid():
        return False

    payload = json.dumps([{"token": t, "all": a, "index": i} for t, a, i in requests])
    fd, path = tempfile.mkstemp(prefix="stiky-notes-", suffix=".js")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(_SCRIPT % payload)
        # Uno script rimasto caricato (es. dopo un crash) impedirebbe il caricamento
        scripting.call("unloadScript", SCRIPT_NAME)
        reply = scripting.call("loadScript", path, SCRIPT_NAME)
        if reply.type() == QDBusMessage.MessageType.ErrorMessage or not reply.arguments():
            return False
        script_id = reply.arguments()[0]
        if script_id < 0:
            return False
        script = QDBusInterface(KWIN_SERVICE, f"/Scripting/Script{script_id}",
                                "org.kde.kwin.Script", bus)
        ok = script.call("run").type() != QDBusMessage.MessageType.ErrorMessage
        scripting.call("unloadScript", SCRIPT_NAME)
        return ok
    finally:
        os.unlink(path)
