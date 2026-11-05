# -*- coding: utf-8 -*-
"""
Controller delle note: esegue le operazioni sul modello e notifica
l'interfaccia tramite segnali.
"""

from typing import List, Optional

from PyQt6.QtCore import QObject, pyqtSignal

from .note_model import NoteData, NoteModel

# Colori disponibili per le note, con il nome mostrato nel menu
COLORS = [
    ("#FFD93D", "Giallo"),
    ("#6BCF7F", "Verde"),
    ("#4A90E2", "Blu"),
    ("#F75C5C", "Rosso"),
    ("#A38DE5", "Viola"),
    ("#50C878", "Verde erba"),
    ("#FFA07A", "Salmone"),
    ("#20B2AA", "Turchese"),
    ("#FF69B4", "Rosa"),
    ("#87CEEB", "Azzurro"),
    ("#FFD700", "Oro"),
    ("#CD5C5C", "Rosso indiano"),
]
COLOR_PALETTE = [hex_ for hex_, _name in COLORS]


class NoteController(QObject):
    """Operazioni sulle note con notifica delle modifiche"""

    note_created = pyqtSignal(dict)
    note_updated = pyqtSignal(dict)
    note_deleted = pyqtSignal(str)

    def __init__(self, model: NoteModel):
        super().__init__()
        self.model = model

    def create_note(self, title: str = "", content: str = "", x: int = 0, y: int = 0,
                    color: str = COLOR_PALETTE[0]) -> Optional[str]:
        """Crea una nuova nota e ne restituisce l'ID"""
        note = self.model.add_note(title, content, x, y, color)
        self.note_created.emit(note.to_dict())
        return note.id

    def update_note(self, note_id: str, **kwargs) -> bool:
        """Aggiorna i campi indicati di una nota"""
        if not self.model.update_note(note_id, **kwargs):
            return False
        note = self.model.get_note(note_id)
        if note is not None:
            self.note_updated.emit(note.to_dict())
        return True

    def delete_note(self, note_id: str) -> bool:
        """Elimina una nota"""
        if not self.model.remove_note(note_id):
            return False
        self.note_deleted.emit(note_id)
        return True

    def toggle_pinned(self, note_id: str) -> bool:
        """Inverte lo stato "fissata" di una nota"""
        note = self.model.get_note(note_id)
        if note is None:
            return False
        return self.update_note(note_id, is_pinned=not note.is_pinned)

    @staticmethod
    def label_for(note: NoteData, max_len: int = 40) -> str:
        """Nome breve della nota: titolo, oppure prima riga del contenuto"""
        text = note.title.strip()
        if not text:
            lines = [line.strip() for line in note.content.splitlines() if line.strip()]
            text = lines[0] if lines else "Nota vuota"
        return text if len(text) <= max_len else text[: max_len - 1] + "…"

    @staticmethod
    def get_color_palette() -> List[str]:
        """Colori disponibili per le note"""
        return list(COLOR_PALETTE)
