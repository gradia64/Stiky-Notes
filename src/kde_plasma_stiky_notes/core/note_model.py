# -*- coding: utf-8 -*-
"""
Modello dati delle note di Stiky-notes.

Ogni nota è un'istanza di NoteData, salvata con QSettings sotto la chiave
``note_<id>`` a ogni modifica (~/.config/StikyNotes/NoteModel.conf).
"""

from dataclasses import dataclass, field, fields
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from PyQt6.QtCore import QObject, QSettings


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class NoteData:
    """Dati di una nota.

    is_pinned significa "sempre in primo piano"; reminder è una data/ora ISO
    8601 con fuso orario. Alcuni campi (formattazione dell'intera nota,
    priorità, tag…) non sono usati dall'interfaccia ma restano nello schema
    per compatibilità con le note già salvate.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    content: str = ""
    color: str = "#FFD93D"  # Giallo
    font_family: str = "Sans Serif"
    font_size: int = 12
    is_bold: bool = False
    is_italic: bool = False
    is_underlined: bool = False
    is_strikethrough: bool = False
    is_monospace: bool = False
    x: int = 0
    y: int = 0
    width: int = 250
    height: int = 250
    z_index: int = 0
    is_minimized: bool = False
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    tags: List[str] = field(default_factory=list)
    is_locked: bool = False
    is_pinned: bool = False
    priority: int = 0
    reminder: Optional[str] = None
    last_focused: Optional[str] = None
    is_visible: bool = True
    # Testo formattato (HTML di Qt); "content" resta il testo semplice
    rich_content: str = ""
    # Desktop virtuale: -1 = deciso dal window manager
    desktop: int = -1
    all_desktops: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Serializza la nota in un dizionario"""
        data = {f.name: getattr(self, f.name) for f in fields(self)}
        data["tags"] = list(self.tags)
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NoteData":
        """Deserializza un dizionario in un'istanza di NoteData.

        Le chiavi sconosciute (es. dati salvati da versioni diverse) vengono
        ignorate e quelle mancanti assumono il valore predefinito, così una
        modifica dello schema non impedisce il caricamento delle note.
        """
        known = {f.name for f in fields(cls)}
        note = cls(**{k: v for k, v in dict(data).items() if k in known})
        if not isinstance(note.tags, list):
            note.tags = list(note.tags) if note.tags else []
        return note


class NoteModel(QObject):
    """Archivio delle note con persistenza automatica su QSettings"""

    def __init__(self):
        super().__init__()
        self._settings = QSettings("StikyNotes", "NoteModel")
        self._notes: Dict[str, NoteData] = {}
        self._next_z_index = 1
        self._load_notes_from_storage()

    # ===== Persistenza =====

    @staticmethod
    def _storage_key(note_id: str) -> str:
        return f"note_{note_id}"

    def _save_note_to_storage(self, note: NoteData):
        self._settings.setValue(self._storage_key(note.id), note.to_dict())

    def _load_notes_from_storage(self):
        """Carica tutte le note salvate"""
        for key in self._settings.allKeys():
            if not key.startswith("note_"):
                continue
            # Una nota corrotta non deve impedire il caricamento delle altre
            try:
                note_dict = self._settings.value(key)
                if note_dict:
                    note = NoteData.from_dict(note_dict)
                    self._notes[note.id] = note
            except Exception as e:
                print(f"[NoteModel] Nota '{key}' ignorata (dati non validi): {e}")

        # Riprende la numerazione dello z-index dopo quella delle note salvate
        if self._notes:
            self._next_z_index = max(n.z_index for n in self._notes.values()) + 1

    # ===== API =====

    def add_note(self, title: str = "", content: str = "", x: int = 0, y: int = 0,
                 color: str = "#FFD93D") -> NoteData:
        """Crea una nuova nota e la salva"""
        note = NoteData(title=title, content=content, x=x, y=y, color=color,
                        z_index=self._next_z_index)
        self._next_z_index += 1
        self._notes[note.id] = note
        self._save_note_to_storage(note)
        return note

    def update_note(self, note_id: str, **kwargs) -> bool:
        """Aggiorna i campi indicati di una nota esistente"""
        note = self._notes.get(note_id)
        if note is None:
            return False
        for key, value in kwargs.items():
            if hasattr(note, key):
                setattr(note, key, value)
        note.updated_at = _now()
        self._save_note_to_storage(note)
        return True

    def remove_note(self, note_id: str) -> bool:
        """Elimina una nota"""
        if self._notes.pop(note_id, None) is None:
            return False
        self._settings.remove(self._storage_key(note_id))
        return True

    def get_note(self, note_id: str) -> Optional[NoteData]:
        """Restituisce una nota, o None se non esiste"""
        return self._notes.get(note_id)

    def get_all_notes(self) -> List[NoteData]:
        """Tutte le note, prima le fissate e poi per data di creazione.

        L'ordinamento esplicito serve perché QSettings rilegge le chiavi in
        ordine alfabetico dell'UUID: l'ordine di inserimento non sopravvive
        al riavvio.
        """
        return sorted(self._notes.values(), key=lambda n: (not n.is_pinned, n.created_at))
