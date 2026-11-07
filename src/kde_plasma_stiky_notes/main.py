# -*- coding: utf-8 -*-
"""
Stiky-notes - note adesive (post-it) sul desktop di KDE Plasma.

Ogni nota è una finestra a sé (qml/NoteWindow.qml) che si sposta, si
ridimensiona e si colora liberamente; posizione, dimensioni e testo vengono
salvati automaticamente. L'applicazione vive nell'area di notifica.

Flusso di avvio: scelta della piattaforma (XWayland su Wayland, per poter
riposizionare le note) -> QApplication -> controllo istanza singola (D-Bus)
-> StikyNotesApp (modello, controller, finestre, vassoio) -> ciclo eventi.

Argomenti: --new (nuova nota), --show-all (mostra tutte le note),
--autostart (avvio al login: mostra solo le note già visibili).
Se un'istanza è già attiva, la richiesta le viene inoltrata.
"""

import argparse
import os
import sys
from typing import Tuple

from PyQt6.QtCore import QObject, QTimer, pyqtSlot
from PyQt6.QtGui import QCursor, QGuiApplication, QIcon, QKeySequence
from PyQt6.QtQml import QQmlEngine
from PyQt6.QtWidgets import QApplication, QMenu, QMessageBox

from . import __version__
from .core import reminders
from .core.note_controller import COLORS, NoteController
from .core.note_model import NoteModel
from .platform import kwin_desktops
from .platform.single_instance import SingleInstanceService, forward_to_running_instance
from .ui import reminder_dialog, text_format
from .ui.note_windows import NoteWindowManager
from .ui.tray_manager import TrayManager, app_icon, color_icon

CASCADE_STEP = 32
CASCADE_STEPS = 8
REMINDER_CHECK_MS = 15_000
# Attesa perché KWin veda il titolo temporaneo della finestra (e poi lo script)
KWIN_CAPTION_DELAY_MS = 300


class StikyNotesApp(QObject):
    """Collega modello, finestre delle note e vassoio; bridge per QML ("stikyApp")."""

    def __init__(self, engine: QQmlEngine):
        super().__init__()
        self.note_model = NoteModel()
        self.note_controller = NoteController(self.note_model)
        self.tray_manager = TrayManager(self)
        self._cleaned_up = False
        self._cascade = 0
        # Su Wayland nativo l'applicazione non conosce né decide la posizione
        # delle proprie finestre: in quel caso si salvano solo le dimensioni.
        self._can_position = QGuiApplication.platformName() != "wayland"

        engine.rootContext().setContextProperty("stikyApp", self)
        self.windows = NoteWindowManager(engine, self)

        self.note_controller.note_created.connect(self._on_note_created)
        self.note_controller.note_updated.connect(self._on_note_updated)
        self.note_controller.note_deleted.connect(self._on_note_deleted)

        self.tray_manager.new_note_requested.connect(self.create_new_note)
        self.tray_manager.show_all_requested.connect(self.show_all_notes)
        self.tray_manager.hide_all_requested.connect(self.hide_all_notes)
        self.tray_manager.note_activated.connect(self.show_note)
        self.tray_manager.message_clicked.connect(self._on_notification_clicked)

        self._last_reminder_note = ""
        self._reminder_timer = QTimer(self)
        self._reminder_timer.setInterval(REMINDER_CHECK_MS)
        self._reminder_timer.timeout.connect(self.check_reminders)

    # ===== Avvio =====

    def open_saved_notes(self):
        """Crea le finestre delle note salvate e avvia il controllo dei promemoria"""
        notes = self.note_model.get_all_notes()
        for note in notes:
            self.windows.open(note)
        self._refresh_tray()
        self.apply_desktops([n.id for n in notes if n.is_visible])
        # I promemoria scaduti mentre l'app era chiusa scattano subito
        self.check_reminders()
        self._reminder_timer.start()

    def show_on_launch(self):
        """Avvio esplicito dell'utente: le note devono comparire"""
        notes = self.note_model.get_all_notes()
        if not notes:
            self.create_new_note()
        else:
            self.show_all_notes()

    # ===== Aggiornamenti dal controller =====

    def _on_note_created(self, data: dict):
        note = self.note_model.get_note(data["id"])
        if note is not None:
            self.windows.open(note)
            self.windows.show(note.id, focus=True)
        self._refresh_tray()

    def _on_note_updated(self, data: dict):
        note_id = data["id"]
        self.windows.set_property(note_id, "noteColor", data["color"])
        self.windows.set_property(note_id, "keepAbove", data["is_pinned"])
        self.windows.set_property(note_id, "reminderText", reminders.short_label(data["reminder"]))
        self._refresh_tray()

    def _on_note_deleted(self, note_id: str):
        self.windows.close(note_id)
        self._refresh_tray()

    def _refresh_tray(self):
        self.tray_manager.set_notes([
            (n.id, NoteController.label_for(n), n.color)
            for n in self.note_model.get_all_notes()
        ])

    # ===== Azioni =====

    def _new_note_position(self, width: int, height: int) -> Tuple[int, int]:
        """Posizione a cascata partendo dall'angolo in alto a destra dello schermo"""
        screen = QGuiApplication.primaryScreen().availableGeometry()
        step = self._cascade % CASCADE_STEPS
        self._cascade += 1
        x = screen.right() - width - 48 - step * CASCADE_STEP
        y = screen.top() + 48 + step * CASCADE_STEP
        return max(screen.left(), x), min(y, max(screen.top(), screen.bottom() - height))

    @pyqtSlot(result=str)
    def create_new_note(self) -> str:
        """Crea una nuova nota e ne apre la finestra"""
        size = 250
        x, y = self._new_note_position(size, size)
        return self.note_controller.create_note(x=x, y=y) or ""

    @pyqtSlot(str)
    def show_note(self, note_id: str):
        """Mostra una nota (anche se era nascosta) in primo piano"""
        note = self.note_model.get_note(note_id)
        if note is None:
            return
        was_hidden = not note.is_visible
        if was_hidden:
            self.note_model.update_note(note_id, is_visible=True)
        self.windows.show(note_id, focus=True)
        if was_hidden:
            self.apply_desktops([note_id])

    def show_all_notes(self):
        reopened = []
        for note in self.note_model.get_all_notes():
            if not note.is_visible:
                self.note_model.update_note(note.id, is_visible=True)
                reopened.append(note.id)
            self.windows.show(note.id)
        self.apply_desktops(reopened)

    def hide_all_notes(self):
        self.windows.flush_all()
        for note in self.note_model.get_all_notes():
            if note.is_visible:
                self.note_model.update_note(note.id, is_visible=False)
            self.windows.hide(note.id)

    # ===== Bridge per QML (devono essere slot per essere visibili da QML) =====

    @pyqtSlot(str)
    def hide_note(self, note_id: str):
        note = self.note_model.get_note(note_id)
        if note is not None and note.is_visible:
            self.note_model.update_note(note_id, is_visible=False)
        self.windows.hide(note_id)

    @pyqtSlot(str, str)
    def update_note_title(self, note_id: str, title: str):
        self.note_controller.update_note(note_id, title=title)

    @pyqtSlot(str, str, str)
    def update_note_content(self, note_id: str, plain: str, rich: str):
        """Salva il testo: semplice (etichette, ricerca) e formattato (HTML)"""
        self.note_controller.update_note(note_id, content=plain, rich_content=rich)

    @pyqtSlot(str, str, int, int, int)
    def format_text(self, note_id: str, action: str, start: int, end: int, cursor: int):
        """Formattazione dalla barra o dalle scorciatoie (Ctrl+B/I/U)"""
        doc = self.windows.document(note_id)
        if doc is not None and action in text_format.ACTIONS:
            text_format.apply_format(doc, action, start, end, cursor)

    @pyqtSlot(str, bool, bool, bool, bool, bool, result=str)
    def show_text_menu(self, note_id: str, has_selection: bool, can_paste: bool,
                       can_undo: bool, can_redo: bool, has_text: bool) -> str:
        """Menu del clic destro sul testo. Restituisce l'azione scelta ("" se
        nessuna); la esegue il QML sul TextEdit."""
        menu = QMenu()
        actions = {}

        def add(target, key, label, icon, shortcut=None, enabled=True):
            action = target.addAction(QIcon.fromTheme(icon), label)
            if shortcut:
                action.setShortcut(QKeySequence(shortcut))
            action.setEnabled(enabled)
            actions[action] = key

        add(menu, "undo", "Annulla", "edit-undo", "Ctrl+Z", can_undo)
        add(menu, "redo", "Ripeti", "edit-redo", "Ctrl+Shift+Z", can_redo)
        menu.addSeparator()
        add(menu, "cut", "Taglia", "edit-cut", "Ctrl+X", has_selection)
        add(menu, "copy", "Copia", "edit-copy", "Ctrl+C", has_selection)
        add(menu, "paste", "Incolla", "edit-paste", "Ctrl+V", can_paste)
        add(menu, "delete", "Elimina", "edit-delete", None, has_selection)
        menu.addSeparator()
        add(menu, "selectAll", "Seleziona tutto", "edit-select-all", "Ctrl+A", has_text)
        menu.addSeparator()
        fmt = menu.addMenu(QIcon.fromTheme("format-text-bold"), "Formato")
        add(fmt, "bold", "Grassetto", "format-text-bold", "Ctrl+B")
        add(fmt, "italic", "Corsivo", "format-text-italic", "Ctrl+I")
        add(fmt, "underline", "Sottolineato", "format-text-underline", "Ctrl+U")
        add(fmt, "strike", "Barrato", "format-text-strikethrough")
        fmt.addSeparator()
        add(fmt, "bullet", "Elenco puntato", "format-list-unordered")
        add(fmt, "numbered", "Elenco numerato", "format-list-ordered")
        fmt.addSeparator()
        add(fmt, "clear", "Rimuovi formattazione", "edit-clear")

        chosen = menu.exec(QCursor.pos())
        return actions.get(chosen, "")

    # ===== Promemoria =====

    @pyqtSlot(str)
    def edit_reminder(self, note_id: str):
        """Imposta, modifica o rimuove il promemoria di una nota"""
        note = self.note_model.get_note(note_id)
        if note is None:
            return
        action, when = reminder_dialog.ask_reminder(NoteController.label_for(note), note.reminder)
        if action == reminder_dialog.SET and when is not None:
            self.note_controller.update_note(note_id, reminder=reminders.serialize(when))
            self.check_reminders()
        elif action == reminder_dialog.REMOVE:
            self.note_controller.update_note(note_id, reminder=None)

    def check_reminders(self):
        """Fa scattare i promemoria scaduti e aggiorna le etichette ("oggi", giorno…)"""
        for note in self.note_model.get_all_notes():
            if not note.reminder:
                continue
            if reminders.is_due(note.reminder):
                self._fire_reminder(note.id)
            else:
                self.windows.set_property(note.id, "reminderText",
                                          reminders.short_label(note.reminder))

    def _fire_reminder(self, note_id: str):
        note = self.note_model.get_note(note_id)
        if note is None:
            return
        self.note_controller.update_note(note_id, reminder=None)
        self.show_note(note_id)
        self._last_reminder_note = note_id
        self.tray_manager.notify("Promemoria", NoteController.label_for(note, max_len=80))

    def _on_notification_clicked(self):
        if self._last_reminder_note:
            self.show_note(self._last_reminder_note)

    # ===== Desktop virtuali =====

    def apply_desktops(self, note_ids):
        """Porta le note indicate sul desktop scelto (o su tutti) tramite KWin.

        La finestra viene riconosciuta da KWin con un titolo temporaneo
        univoco, ripristinato subito dopo l'esecuzione dello script.
        """
        requests = []
        for note_id in note_ids:
            note = self.note_model.get_note(note_id)
            if note is None or not (note.all_desktops or note.desktop >= 0):
                continue
            token = kwin_desktops.token_for(note_id)
            requests.append((note_id, token, note.all_desktops, note.desktop))
        if not requests or not kwin_desktops.available():
            return
        for note_id, token, _all, _index in requests:
            self.windows.set_property(note_id, "captionOverride", token)

        def run():
            kwin_desktops.apply([(token, all_, index) for _id, token, all_, index in requests])
            QTimer.singleShot(KWIN_CAPTION_DELAY_MS, restore)

        def restore():
            for note_id, _token, _all, _index in requests:
                self.windows.set_property(note_id, "captionOverride", "")

        QTimer.singleShot(KWIN_CAPTION_DELAY_MS, run)

    def _set_desktop(self, note_id: str, all_desktops: bool, index: int):
        self.note_model.update_note(note_id, all_desktops=all_desktops, desktop=index)
        self.apply_desktops([note_id])

    @pyqtSlot(str, int, int, int, int)
    def update_note_geometry(self, note_id: str, x: int, y: int, width: int, height: int):
        """Salva posizione e dimensioni (senza notificare: non cambia nulla per la UI)"""
        note = self.note_model.get_note(note_id)
        if note is None:
            return
        changes = {"width": width, "height": height}
        if self._can_position:
            changes.update(x=x, y=y)
        changes = {k: v for k, v in changes.items() if getattr(note, k) != v}
        if changes:
            self.note_model.update_note(note_id, **changes)

    @pyqtSlot(str)
    def show_note_menu(self, note_id: str):
        """Menu della nota (pulsante ⋮ o clic destro sulla barra)"""
        note = self.note_model.get_note(note_id)
        if note is None:
            return

        menu = QMenu()
        new_action = menu.addAction("Nuova nota")
        rename_action = menu.addAction("Rinomina…")

        color_menu = menu.addMenu("Colore")
        color_actions = {}
        for hex_, name in COLORS:
            action = color_menu.addAction(color_icon(hex_, square=True), name)
            action.setCheckable(True)
            action.setChecked(hex_.lower() == note.color.lower())
            color_actions[action] = hex_

        above_action = menu.addAction("Sempre in primo piano")
        above_action.setCheckable(True)
        above_action.setChecked(note.is_pinned)

        # Desktop virtuali (solo se KWin è disponibile)
        desktop_actions = {}
        names = kwin_desktops.desktop_names() if kwin_desktops.available() else []
        if names:
            desktop_menu = menu.addMenu("Desktop")
            all_action = desktop_menu.addAction("Tutti i desktop")
            all_action.setCheckable(True)
            all_action.setChecked(note.all_desktops)
            desktop_actions[all_action] = (True, -1)
            desktop_menu.addSeparator()
            for index, name in enumerate(names):
                action = desktop_menu.addAction(name)
                action.setCheckable(True)
                action.setChecked(not note.all_desktops and note.desktop == index)
                desktop_actions[action] = (False, index)

        menu.addSeparator()
        reminder_action = menu.addAction(
            "Modifica promemoria…" if note.reminder else "Promemoria…"
        )
        remove_reminder_action = None
        if note.reminder:
            remove_reminder_action = menu.addAction("Rimuovi promemoria")

        menu.addSeparator()
        hide_action = menu.addAction("Nascondi")
        delete_action = menu.addAction("Elimina…")

        chosen = menu.exec(QCursor.pos())
        if chosen is None:
            return
        if chosen is new_action:
            self.create_new_note()
        elif chosen is rename_action:
            self.windows.edit_title(note_id)
        elif chosen in color_actions:
            self.note_controller.update_note(note_id, color=color_actions[chosen])
        elif chosen is above_action:
            self.note_controller.toggle_pinned(note_id)
        elif chosen in desktop_actions:
            all_desktops, index = desktop_actions[chosen]
            if all_desktops and note.all_desktops:
                # Deseleziona "Tutti i desktop": la nota resta solo su quello attuale
                all_desktops, index = False, -1
            self._set_desktop(note_id, all_desktops, index)
        elif chosen is reminder_action:
            self.edit_reminder(note_id)
        elif remove_reminder_action is not None and chosen is remove_reminder_action:
            self.note_controller.update_note(note_id, reminder=None)
        elif chosen is hide_action:
            self.windows.flush_all()
            self.hide_note(note_id)
        elif chosen is delete_action:
            self.delete_note(note_id)

    def delete_note(self, note_id: str):
        """Elimina una nota, chiedendo conferma se non è vuota"""
        self.windows.flush_all()
        note = self.note_model.get_note(note_id)
        if note is None:
            return
        if note.title.strip() or note.content.strip():
            answer = QMessageBox.question(
                None,
                "Elimina nota",
                f"Eliminare definitivamente la nota «{NoteController.label_for(note)}»?",
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        self.note_controller.delete_note(note_id)

    # ===== Chiusura =====

    def cleanup(self):
        """Salva e rilascia le risorse (idempotente: aboutToQuit e teardown)"""
        if self._cleaned_up:
            return
        self._cleaned_up = True
        self._reminder_timer.stop()

        # Salva le modifiche digitate negli ultimi istanti
        self.windows.flush_all()

        # Blocca i segnali: nessuno slot Python deve essere invocato durante la
        # distruzione del motore QML (in PyQt6 un'eccezione in uno slot
        # richiamato da C++ in fase di shutdown termina il processo con SIGABRT).
        self.note_controller.blockSignals(True)
        self.tray_manager.blockSignals(True)
        self.tray_manager.cleanup()


def _parse_args(argv):
    """Gestisce gli argomenti da riga di comando"""
    parser = argparse.ArgumentParser(
        prog="stiky-notes",
        description="Note adesive (post-it) per KDE Plasma",
    )
    parser.add_argument("--new", action="store_true", help="Crea una nuova nota")
    parser.add_argument("--show-all", action="store_true", help="Mostra tutte le note")
    parser.add_argument(
        "--autostart", action="store_true",
        help="Avvio al login: mostra solo le note lasciate visibili",
    )
    # Gli argomenti sconosciuti (es. flag di Qt) vengono ignorati
    args, _unknown = parser.parse_known_args(argv)
    return args


def _choose_platform():
    """Su Wayland usa XWayland, salvo diversa indicazione.

    Wayland non permette a un'applicazione di posizionare le proprie
    finestre: le note tornerebbero dove decide il compositor a ogni avvio.
    Con XWayland ogni post-it riappare esattamente dove lo si era lasciato.
    STIKY_NOTES_WAYLAND=1 forza Wayland nativo; QT_QPA_PLATFORM ha sempre
    la precedenza.
    """
    if (
        os.environ.get("XDG_SESSION_TYPE") == "wayland"
        and "QT_QPA_PLATFORM" not in os.environ
        and os.environ.get("STIKY_NOTES_WAYLAND") != "1"
        and os.environ.get("DISPLAY")
    ):
        os.environ["QT_QPA_PLATFORM"] = "xcb"


def main():
    """Funzione principale dell'applicazione"""

    args = _parse_args(sys.argv[1:])
    _choose_platform()

    app = QApplication(sys.argv)
    app.setApplicationName("Stiky-notes")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("StikyNotes")
    app.setDesktopFileName("stiky-notes")
    app.setWindowIcon(app_icon())
    # Nascondere tutte le note non chiude l'app: si esce dal menu del vassoio
    app.setQuitOnLastWindowClosed(False)

    # ===== Istanza singola =====
    # Un secondo avvio inoltra la richiesta all'istanza attiva ed esce, invece
    # di creare un altro vassoio e un secondo modello che sovrascriverebbe le
    # note salvate dall'altro processo.
    single_instance = SingleInstanceService()
    if not single_instance.register():
        if args.autostart:
            return 0
        method = "NewNote" if args.new else "ShowAll"
        if forward_to_running_instance(method):
            return 0
        print(
            "[StikyNotesApp] Un'altra istanza possiede il nome D-Bus ma non risponde",
            file=sys.stderr,
        )
        return 1

    engine = QQmlEngine()
    try:
        stiky_app = StikyNotesApp(engine)
    except RuntimeError as e:
        print(f"[StikyNotesApp] {e}", file=sys.stderr)
        return 1

    single_instance.new_note_requested.connect(stiky_app.create_new_note)
    single_instance.show_all_requested.connect(stiky_app.show_all_notes)

    stiky_app.open_saved_notes()
    if args.new:
        stiky_app.create_new_note()
    elif not args.autostart:
        stiky_app.show_on_launch()

    stiky_app.tray_manager.show_tray_icon()
    app.aboutToQuit.connect(stiky_app.cleanup)

    exit_code = app.exec()

    # ===== Teardown deterministico e ordinato =====
    # 1. Salva e blocca i segnali Python.
    # 2. Distruggi le finestre delle note e sgancia il contesto QML da Python,
    #    poi il motore QML, mentre QApplication è ancora vivo.
    # 3. Distruggi l'applicazione (modello/controller/tray).
    stiky_app.cleanup()  # idempotente
    single_instance.unregister()
    stiky_app.windows.destroy_all()
    engine.rootContext().setContextProperty("stikyApp", None)
    del engine
    del stiky_app

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
