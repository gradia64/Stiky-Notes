# -*- coding: utf-8 -*-
"""
Promemoria delle note.

Il promemoria è salvato in NoteData.reminder come data/ora ISO 8601 con fuso
orario (es. "2026-11-06T09:30:00+01:00"); una data senza fuso viene
interpretata come ora locale.
"""

from datetime import datetime, timedelta
from typing import Optional


def now() -> datetime:
    """Ora locale con fuso orario"""
    return datetime.now().astimezone()


def parse(value: Optional[str]) -> Optional[datetime]:
    """Data/ora del promemoria, o None se assente o non valida"""
    if not value:
        return None
    try:
        when = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    if when.tzinfo is None:
        when = when.astimezone()
    return when


def serialize(when: datetime) -> str:
    """Formato di salvataggio (secondi azzerati, fuso orario locale)"""
    if when.tzinfo is None:
        when = when.astimezone()
    return when.replace(second=0, microsecond=0).isoformat()


def is_due(value: Optional[str], at: Optional[datetime] = None) -> bool:
    """True se il promemoria è scaduto"""
    when = parse(value)
    return when is not None and when <= (at or now())


def short_label(value: Optional[str], at: Optional[datetime] = None) -> str:
    """Testo breve per la barra della nota: "14:30", "dom 14:30" o "12/11 14:30"."""
    when = parse(value)
    if when is None:
        return ""
    local = when.astimezone()
    today = (at or now()).astimezone().date()
    days = ["lun", "mar", "mer", "gio", "ven", "sab", "dom"]
    if local.date() == today:
        return local.strftime("%H:%M")
    if today < local.date() < today + timedelta(days=7):
        return f"{days[local.weekday()]} {local.strftime('%H:%M')}"
    return local.strftime("%d/%m %H:%M")


def default_time(at: Optional[datetime] = None) -> datetime:
    """Proposta iniziale: tra un'ora, arrotondata al quarto d'ora successivo"""
    base = (at or now()) + timedelta(hours=1)
    minutes = (base.minute // 15 + 1) * 15
    return base.replace(minute=0, second=0, microsecond=0) + timedelta(minutes=minutes)
