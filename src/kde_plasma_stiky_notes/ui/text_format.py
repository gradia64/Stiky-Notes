# -*- coding: utf-8 -*-
"""
Formattazione del testo delle note (grassetto, corsivo, elenchi…).

Le operazioni agiscono sul QTextDocument del TextEdit della nota, così
restano annullabili con Ctrl+Z e il TextEdit si aggiorna da solo.
"""

import html

from PyQt6.QtGui import QFont, QTextCharFormat, QTextCursor, QTextDocument, QTextListFormat

ACTIONS = ("bold", "italic", "underline", "strike", "bullet", "numbered", "clear")

_LIST_STYLES = {
    "bullet": QTextListFormat.Style.ListDisc,
    "numbered": QTextListFormat.Style.ListDecimal,
}


def plain_to_html(text: str) -> str:
    """Converte testo semplice (note delle versioni precedenti) in HTML"""
    if not text:
        return ""
    lines = "".join(f"<p>{html.escape(line) or '<br />'}</p>" for line in text.split("\n"))
    return f"<html><body>{lines}</body></html>"


def _selection(doc: QTextDocument, start: int, end: int, cursor_pos: int) -> QTextCursor:
    cursor = QTextCursor(doc)
    if start != end:
        cursor.setPosition(min(start, end))
        cursor.setPosition(max(start, end), QTextCursor.MoveMode.KeepAnchor)
    else:
        cursor.setPosition(min(cursor_pos, doc.characterCount() - 1))
    return cursor


def _toggle_char_format(cursor: QTextCursor, action: str):
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


def _toggle_list(cursor: QTextCursor, action: str):
    style = _LIST_STYLES[action]
    current = cursor.currentList()
    cursor.beginEditBlock()
    if current is not None and current.format().style() == style:
        # Stesso tipo di elenco: lo toglie dai paragrafi selezionati
        doc = cursor.document()
        block = doc.findBlock(cursor.selectionStart())
        last = doc.findBlock(cursor.selectionEnd())
        while block.isValid():
            block_list = block.textList()
            if block_list is not None:
                block_list.remove(block)
                block_cursor = QTextCursor(block)
                block_format = block_cursor.blockFormat()
                block_format.setIndent(0)
                block_cursor.setBlockFormat(block_format)
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


def _clear(cursor: QTextCursor):
    if not cursor.hasSelection():
        cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
    fmt = QTextCharFormat()
    fmt.setFontWeight(QFont.Weight.Normal)
    fmt.setFontItalic(False)
    fmt.setFontUnderline(False)
    fmt.setFontStrikeOut(False)
    cursor.mergeCharFormat(fmt)


def apply_format(doc: QTextDocument, action: str, start: int, end: int, cursor_pos: int):
    """Applica ``action`` (vedi ACTIONS) alla selezione [start, end) del documento"""
    if action not in ACTIONS:
        raise ValueError(f"Formattazione sconosciuta: {action}")
    cursor = _selection(doc, start, end, cursor_pos)
    if action in _LIST_STYLES:
        _toggle_list(cursor, action)
    elif action == "clear":
        _clear(cursor)
    else:
        _toggle_char_format(cursor, action)
