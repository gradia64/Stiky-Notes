# -*- coding: utf-8 -*-
"""
Formattazione del testo delle note (grassetto, corsivo, elenchi…).

Le operazioni agiscono sul QTextDocument del TextEdit della nota, così
restano annullabili con Ctrl+Z e il TextEdit si aggiorna da solo.
"""

import html
from typing import Iterator

from PyQt6.QtGui import (
    QFont,
    QTextBlock,
    QTextCharFormat,
    QTextCursor,
    QTextDocument,
    QTextListFormat,
)

ACTIONS = ("bold", "italic", "underline", "strike", "bullet", "numbered", "clear")

_LIST_STYLES = {
    "bullet": QTextListFormat.Style.ListDisc,
    "numbered": QTextListFormat.Style.ListDecimal,
}

# Proprietà del formato di un paragrafo senza formattazione propria
_PLAIN_BLOCK_CHAR = QTextCharFormat().properties()


def plain_to_html(text: str) -> str:
    """Converte testo semplice (note delle versioni precedenti) in HTML"""
    if not text:
        return ""
    lines = "".join(
        f"<p>{html.escape(line) or '<br />'}</p>" for line in text.split("\n")
    )
    return f"<html><body>{lines}</body></html>"


def _selection(
    doc: QTextDocument, start: int, end: int, cursor_pos: int
) -> QTextCursor:
    cursor = QTextCursor(doc)
    if start != end:
        cursor.setPosition(min(start, end))
        cursor.setPosition(max(start, end), QTextCursor.MoveMode.KeepAnchor)
    else:
        cursor.setPosition(min(cursor_pos, doc.characterCount() - 1))
    return cursor


def _toggle_char_format(cursor: QTextCursor, action: str) -> None:
    if not cursor.hasSelection():
        # Senza selezione si formatta la parola sotto il cursore
        cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        if not cursor.hasSelection():
            return
    # Stato attuale: quello del primo carattere della selezione
    probe = QTextCursor(cursor.document())
    probe.setPosition(cursor.selectionStart() + 1)
    current = probe.charFormat()

    fmt = QTextCharFormat()
    if action == "bold":
        bold = current.fontWeight() >= QFont.Weight.Bold
        fmt.setFontWeight(QFont.Weight.Normal if bold else QFont.Weight.Bold)
    elif action == "italic":
        fmt.setFontItalic(not current.fontItalic())
    elif action == "underline":
        fmt.setFontUnderline(not current.fontUnderline())
    elif action == "strike":
        fmt.setFontStrikeOut(not current.fontStrikeOut())
    cursor.mergeCharFormat(fmt)


def _leave_list(block: QTextBlock) -> None:
    """Toglie il paragrafo dall'elenco senza lasciarlo rientrato.

    ``QTextList.remove`` sposta il rientro dell'elenco sul paragrafo: il
    testo resterebbe spostato a destra anche fuori dall'elenco.
    """
    block_list = block.textList()
    if block_list is None:
        return
    block_list.remove(block)
    block_cursor = QTextCursor(block)
    block_format = block_cursor.blockFormat()
    block_format.setIndent(0)
    block_cursor.setBlockFormat(block_format)


def _needs_fix(block: QTextBlock) -> bool:
    """Il simbolo di una voce d'elenco (pallino o numero) usa il formato del
    paragrafo, non quello del testo: se una voce lo ha in grassetto o con
    un altro font, il simbolo esce più largo e fuori allineamento. Fuori
    dagli elenchi l'app non usa rientri, che restano solo per errore."""
    if block.textList() is not None:
        return block.charFormat().properties() != _PLAIN_BLOCK_CHAR
    return block.blockFormat().indent() != 0


def _fix_block(block: QTextBlock) -> None:
    if not _needs_fix(block):
        return
    block_cursor = QTextCursor(block)
    if block.textList() is not None:
        block_cursor.setBlockCharFormat(QTextCharFormat())
    else:
        block_format = block.blockFormat()
        block_format.setIndent(0)
        block_cursor.setBlockFormat(block_format)


def _blocks(doc: QTextDocument) -> Iterator[QTextBlock]:
    block = doc.begin()
    while block.isValid():
        yield block
        block = block.next()


def normalize_lists(doc: QTextDocument) -> bool:
    """Ripara gli elenchi salvati dalle versioni precedenti (simboli
    disallineati, testo rientrato dopo l'elenco). Da chiamare subito dopo
    aver caricato la nota: la correzione non entra nella cronologia di
    Ctrl+Z. Restituisce True se ha cambiato qualcosa."""
    if not any(_needs_fix(block) for block in _blocks(doc)):
        return False
    doc.setUndoRedoEnabled(False)
    for block in list(_blocks(doc)):
        _fix_block(block)
    doc.setUndoRedoEnabled(True)
    return True


def list_key(doc: QTextDocument, key: str, position: int) -> int:
    """Invio e Backspace dentro un elenco (senza selezione).

    - Invio su una voce vuota chiude l'elenco; su una voce piena ne crea
      una nuova con il simbolo nel formato normale.
    - Backspace all'inizio di una voce la toglie dall'elenco, senza rientro.

    Restituisce la nuova posizione del cursore, o -1 se il tasto va
    lasciato al TextEdit.
    """
    cursor = QTextCursor(doc)
    cursor.setPosition(min(position, doc.characterCount() - 1))
    block = cursor.block()
    if block.textList() is None:
        return -1
    if key == "backspace":
        if not cursor.atBlockStart():
            return -1
        cursor.beginEditBlock()
        _leave_list(block)
        cursor.endEditBlock()
        return cursor.position()
    if key == "enter":
        cursor.beginEditBlock()
        if block.length() <= 1:
            _leave_list(block)
        else:
            cursor.insertBlock(cursor.blockFormat(), QTextCharFormat())
        cursor.endEditBlock()
        return cursor.position()
    return -1


def _toggle_list(cursor: QTextCursor, action: str) -> None:
    style = _LIST_STYLES[action]
    current = cursor.currentList()
    cursor.beginEditBlock()
    if current is not None and current.format().style() == style:
        # Stesso tipo di elenco: lo toglie dai paragrafi selezionati
        doc = cursor.document()
        assert doc is not None
        block = doc.findBlock(cursor.selectionStart())
        last = doc.findBlock(cursor.selectionEnd())
        while block.isValid():
            _leave_list(block)
            if block == last:
                break
            block = block.next()
    elif current is not None:
        # Elenco dell'altro tipo: cambia solo lo stile
        list_format = current.format()
        list_format.setStyle(style)
        current.setFormat(list_format)
    else:
        cursor.createList(style)
    cursor.endEditBlock()


def _clear(cursor: QTextCursor) -> None:
    if not cursor.hasSelection():
        cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
    fmt = QTextCharFormat()
    fmt.setFontWeight(QFont.Weight.Normal)
    fmt.setFontItalic(False)
    fmt.setFontUnderline(False)
    fmt.setFontStrikeOut(False)
    cursor.mergeCharFormat(fmt)


def apply_format(
    doc: QTextDocument, action: str, start: int, end: int, cursor_pos: int
) -> None:
    """Applica ``action`` (vedi ACTIONS) alla selezione [start, end) del documento"""
    if action not in ACTIONS:
        raise ValueError(f"Formattazione sconosciuta: {action}")
    cursor = _selection(doc, start, end, cursor_pos)
    cursor.beginEditBlock()
    if action in _LIST_STYLES:
        _toggle_list(cursor, action)
    elif action == "clear":
        _clear(cursor)
    else:
        _toggle_char_format(cursor, action)
    # Un grassetto su una voce intera finisce anche sul suo simbolo
    first = doc.findBlock(cursor.selectionStart())
    last = doc.findBlock(cursor.selectionEnd())
    block = first
    while block.isValid():
        _fix_block(block)
        if block == last:
            break
        block = block.next()
    cursor.endEditBlock()
