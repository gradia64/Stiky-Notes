# -*- coding: utf-8 -*-
"""
Gestione dell'avvio automatico secondo la specifica XDG Autostart.

Il pacchetto installa /etc/xdg/autostart/stiky-notes.desktop. Per disattivarlo
per il solo utente si crea ~/.config/autostart/stiky-notes.desktop con
``Hidden=true`` (un file utente con lo stesso nome ha la precedenza su quello
di sistema). Per riattivarlo si rimuove l'override, oppure, se non esiste un
file di sistema (es. installazione con pip), si scrive una voce utente attiva.
"""

import os
from pathlib import Path
from typing import List

APP_ID = "stiky-notes"


def _autostart_entry(hidden: bool) -> str:
    """Contenuto della voce di autostart dell'utente."""
    return (
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name=Stiky-notes\n"
        f"Exec={APP_ID} --autostart\n"
        f"Icon={APP_ID}\n"
        "Comment=Avvia Stiky-notes all'accesso al desktop\n"
        f"Hidden={'true' if hidden else 'false'}\n"
        "X-KDE-autostart-after=panel\n"
        "OnlyShowIn=KDE;\n"
    )


def _user_file() -> Path:
    config_home = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return Path(config_home) / "autostart" / f"{APP_ID}.desktop"


def _system_files() -> List[Path]:
    dirs = os.environ.get("XDG_CONFIG_DIRS") or "/etc/xdg"
    return [Path(d) / "autostart" / f"{APP_ID}.desktop" for d in dirs.split(":") if d]


def _is_hidden(path: Path) -> bool:
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            key, _, value = line.partition("=")
            if key.strip() == "Hidden":
                return value.strip().lower() == "true"
    except OSError:
        pass
    return False


def is_enabled() -> bool:
    """True se l'applicazione verrà avviata all'accesso."""
    user = _user_file()
    if user.exists():
        return not _is_hidden(user)
    return any(p.exists() and not _is_hidden(p) for p in _system_files())


def set_enabled(enabled: bool) -> bool:
    """Attiva/disattiva l'avvio automatico per l'utente corrente."""
    user = _user_file()
    try:
        if enabled and any(p.exists() and not _is_hidden(p) for p in _system_files()):
            # Basta rimuovere l'override utente: vale la voce di sistema
            if user.exists():
                user.unlink()
            return True
        user.parent.mkdir(parents=True, exist_ok=True)
        user.write_text(_autostart_entry(hidden=not enabled), encoding="utf-8")
        return True
    except OSError as e:
        print(f"[autostart] Errore: {e}")
        return False
