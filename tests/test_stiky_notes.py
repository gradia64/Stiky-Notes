# -*- coding: utf-8 -*-
"""Test per Stiky-notes: modello, controller e avvio automatico."""

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Aggiungi la directory src al path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from kde_plasma_stiky_notes.core.note_controller import NoteController  # noqa: E402
from kde_plasma_stiky_notes.core.note_model import NoteData, NoteModel  # noqa: E402
from kde_plasma_stiky_notes.platform import autostart  # noqa: E402

QSETTINGS = "kde_plasma_stiky_notes.core.note_model.QSettings"

_QAPP = []


def _qapp():
    """QApplication condivisa, tenuta in vita per tutta la sessione di test."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt6.QtWidgets import QApplication

    if not _QAPP:
        _QAPP.append(QApplication.instance() or QApplication([]))
    return _QAPP[0]


@pytest.fixture
def model():
    # QSettings simulato per evitare scritture su disco
    with patch(QSETTINGS):
        yield NoteModel()


@pytest.fixture
def controller(model):
    return NoteController(model)


# ===== NoteData =====


class TestNoteData:
    def test_creation(self):
        note = NoteData(title="Test", content="Contenuto", color="#FFD93D")
        assert note.title == "Test"
        assert note.content == "Contenuto"
        assert note.id
        assert note.created_at

    def test_serialization_roundtrip(self):
        original = NoteData(title="T", content="C", color="#6BCF7F", x=100, y=200,
                            tags=["tag1", "tag2"])
        data = original.to_dict()
        assert data["title"] == "T"
        assert data["tags"] == ["tag1", "tag2"]
        assert NoteData.from_dict(data) == original

    def test_from_dict_ignores_unknown_and_missing_keys(self):
        note = NoteData.from_dict({"id": "abc", "title": "T", "obsolete_field": 1})
        assert note.id == "abc"
        assert note.title == "T"
        assert note.tags == []


# ===== NoteModel =====


class TestNoteModel:
    def test_add_note(self, model):
        note = model.add_note(title="Test", content="Content", x=10, y=20)
        assert (note.title, note.content, note.x, note.y) == ("Test", "Content", 10, 20)
        assert model.get_note(note.id) is note

    def test_update_note(self, model):
        note = model.add_note(title="Original")
        assert model.update_note(note.id, title="Updated", content="New") is True
        assert model.get_note(note.id).title == "Updated"
        assert model.update_note("missing", title="x") is False

    def test_remove_note(self, model):
        note = model.add_note(title="To Delete")
        assert model.remove_note(note.id) is True
        assert model.get_note(note.id) is None
        assert model.remove_note(note.id) is False

    def test_get_all_notes_is_ordered(self, model):
        a = model.add_note(title="a")
        b = model.add_note(title="b")
        model.update_note(a.id, created_at="2026-01-02T00:00:00+00:00")
        model.update_note(b.id, created_at="2026-01-01T00:00:00+00:00")
        assert [n.title for n in model.get_all_notes()] == ["b", "a"]
        model.update_note(a.id, is_pinned=True)
        assert [n.title for n in model.get_all_notes()] == ["a", "b"]

    def test_load_skips_corrupt_notes_and_restores_z_index(self):
        good = NoteData(title="ok", z_index=7).to_dict()
        # "note_bad" non è un dizionario: from_dict fallisce e la nota va saltata
        stored = {"note_bad": "corrotta", "note_good": good}

        with patch(QSETTINGS) as qs:
            qs.return_value.allKeys.return_value = list(stored)
            qs.return_value.value.side_effect = lambda k: stored[k]
            model = NoteModel()
            assert [n.title for n in model.get_all_notes()] == ["ok"]
            assert model.add_note(title="new").z_index == 8


# ===== NoteController =====


class TestNoteController:
    def test_create_note_emits(self, controller):
        created = []
        controller.note_created.connect(created.append)
        note_id = controller.create_note(title="Nota", content="Contenuto")
        assert controller.model.get_note(note_id).title == "Nota"
        assert created and created[0]["id"] == note_id

    def test_update_note_emits(self, controller):
        note_id = controller.create_note(title="Original")
        updated = []
        controller.note_updated.connect(updated.append)
        assert controller.update_note(note_id, title="Updated", color="#4A90E2") is True
        assert updated[0]["title"] == "Updated"
        assert controller.update_note("missing", title="x") is False

    def test_delete_note_emits(self, controller):
        note_id = controller.create_note(title="To Delete")
        deleted = []
        controller.note_deleted.connect(deleted.append)
        assert controller.delete_note(note_id) is True
        assert deleted == [note_id]
        assert controller.delete_note(note_id) is False

    def test_toggle_pinned(self, controller):
        note_id = controller.create_note()
        assert controller.toggle_pinned(note_id) is True
        assert controller.model.get_note(note_id).is_pinned is True
        controller.toggle_pinned(note_id)
        assert controller.model.get_note(note_id).is_pinned is False
        assert controller.toggle_pinned("missing") is False

    def test_color_palette(self, controller):
        palette = controller.get_color_palette()
        assert len(palette) == 12
        assert palette[0] == "#FFD93D"
        palette.clear()  # restituisce una copia
        assert len(controller.get_color_palette()) == 12


# ===== Avvio automatico =====


class TestAutostart:
    def _env(self, tmp_path, with_system_entry=True):
        system = tmp_path / "xdg"
        (system / "autostart").mkdir(parents=True)
        if with_system_entry:
            (system / "autostart" / "stiky-notes.desktop").write_text(
                "[Desktop Entry]\nHidden=false\n"
            )
        return {"XDG_CONFIG_HOME": str(tmp_path / "home"), "XDG_CONFIG_DIRS": str(system)}

    def test_toggle_with_system_entry(self, tmp_path):
        user_file = tmp_path / "home" / "autostart" / "stiky-notes.desktop"
        with patch.dict(os.environ, self._env(tmp_path)):
            assert autostart.is_enabled() is True
            assert autostart.set_enabled(False)
            assert autostart.is_enabled() is False
            assert "Hidden=true" in user_file.read_text()
            assert autostart.set_enabled(True)
            assert autostart.is_enabled() is True
            # Con la voce di sistema presente basta rimuovere l'override utente
            assert not user_file.exists()

    def test_toggle_without_system_entry(self, tmp_path):
        user_file = tmp_path / "home" / "autostart" / "stiky-notes.desktop"
        with patch.dict(os.environ, self._env(tmp_path, with_system_entry=False)):
            assert autostart.is_enabled() is False
            assert autostart.set_enabled(True)
            assert autostart.is_enabled() is True
            content = user_file.read_text()
            assert "Exec=stiky-notes" in content
            assert "NotShowIn=" not in content  # mutuamente esclusivo con OnlyShowIn


# ===== Etichette =====


def test_label_for():
    assert NoteController.label_for(NoteData(title="  Spesa ")) == "Spesa"
    assert NoteController.label_for(NoteData(content="\n  prima riga\nseconda")) == "prima riga"
    assert NoteController.label_for(NoteData()) == "Nota vuota"
    assert NoteController.label_for(NoteData(title="x" * 60)).endswith("…")


# ===== Applicazione con finestre (piattaforma offscreen) =====


@pytest.fixture
def stiky_app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt6.QtQml import QQmlEngine
    from PyQt6.QtWidgets import QApplication

    from kde_plasma_stiky_notes.main import StikyNotesApp

    app = QApplication.instance() or QApplication([])
    with patch(QSETTINGS), patch("kde_plasma_stiky_notes.ui.tray_manager.autostart"):
        engine = QQmlEngine()
        stiky = StikyNotesApp(engine)
        yield stiky
        stiky.cleanup()
        stiky.windows.destroy_all()
        engine.rootContext().setContextProperty("stikyApp", None)
        del engine
    assert app is not None


class TestStikyNotesApp:
    def test_launch_without_notes_creates_one(self, stiky_app):
        stiky_app.open_saved_notes()
        stiky_app.show_on_launch()
        notes = stiky_app.note_model.get_all_notes()
        assert len(notes) == 1
        assert stiky_app.windows.get(notes[0].id).isVisible()

    def test_edits_reach_model_and_window(self, stiky_app):
        note_id = stiky_app.create_new_note()
        window = stiky_app.windows.get(note_id)
        stiky_app.update_note_content(note_id, "Latte\nPane", "<p>Latte</p><p>Pane</p>")
        stiky_app.note_controller.update_note(note_id, color="#4A90E2")
        stiky_app.note_controller.toggle_pinned(note_id)
        assert stiky_app.note_model.get_note(note_id).content == "Latte\nPane"
        assert window.property("noteColor").name() == "#4a90e2"
        assert window.property("keepAbove") is True
        assert stiky_app.tray_manager._notes == [(note_id, "Latte", "#4A90E2")]

    def test_tray_click_lists_notes_instead_of_showing_all(self, stiky_app):
        """Clic sull'icona: elenco delle note, quelle nascoste restano nascoste."""
        from PyQt6.QtCore import QPoint
        from PyQt6.QtWidgets import QSystemTrayIcon

        first = stiky_app.create_new_note()
        second = stiky_app.create_new_note()
        stiky_app.update_note_content(second, "Spesa", "<p>Spesa</p>")
        stiky_app.hide_all_notes()

        tray = stiky_app.tray_manager
        with patch("kde_plasma_stiky_notes.main.kwin_pointer") as pointer, \
                patch("kde_plasma_stiky_notes.main.QCursor") as cursor:
            pointer.request.return_value = False
            cursor.pos.return_value = QPoint(40, 40)
            tray._on_tray_icon_activated(QSystemTrayIcon.ActivationReason.Trigger)

        assert tray._click_menu.isVisible()
        assert not stiky_app.windows.get(first).isVisible()
        assert not stiky_app.windows.get(second).isVisible()
        labels = [a.text() for a in tray._click_menu.actions() if not a.isSeparator()]
        assert labels == ["Nota vuota", "Spesa", "Nuova nota",
                          "Mostra tutte le note", "Nascondi tutte le note",
                          "Informazioni su Stiky-notes"]

        # Scegliere una nota richiama solo quella
        tray._click_menu.actions()[1].trigger()
        assert stiky_app.windows.get(second).isVisible()
        assert not stiky_app.windows.get(first).isVisible()

        # Un secondo clic sull'icona richiude l'elenco
        tray._on_tray_icon_activated(QSystemTrayIcon.ActivationReason.Trigger)
        assert not tray._click_menu.isVisible()

    def test_tray_menu_opens_where_kwin_reports_the_pointer(self, stiky_app):
        from PyQt6.QtCore import QPoint
        from PyQt6.QtGui import QGuiApplication

        area = QGuiApplication.primaryScreen().virtualGeometry()
        with patch("kde_plasma_stiky_notes.main.kwin_pointer.request", return_value=True), \
                patch.dict(os.environ, {"XDG_SESSION_TYPE": "wayland"}), \
                patch.object(stiky_app.tray_manager, "popup_notes_menu") as popup:
            stiky_app.show_tray_menu()
            popup.assert_not_called()
            # KWin vede lo stesso desktop a scala doppia
            stiky_app.on_pointer_reported(
                200, 100, 0, 0, area.width() * 2, area.height() * 2)
            popup.assert_called_once_with(QPoint(100, 50))
            # Una risposta non attesa viene ignorata
            stiky_app.on_pointer_reported(1, 1, 0, 0, 10, 10)
            popup.assert_called_once()

    def test_about_shows_version_and_project_link(self, stiky_app):
        from kde_plasma_stiky_notes import __version__

        stiky_app.tray_manager.about_requested.emit()
        box = stiky_app._about_box
        assert box.isVisible() and not box.isModal()
        assert __version__ in box.text()
        assert "github.com/gradia64/Stiky-Notes" in box.informativeText()
        assert "GPL" in box.informativeText()
        # Riaprirla non crea una seconda finestra
        stiky_app.show_about()
        assert stiky_app._about_box is box

    def test_geometry_is_saved(self, stiky_app):
        note_id = stiky_app.create_new_note()
        stiky_app.update_note_geometry(note_id, 100, 120, 300, 280)
        note = stiky_app.note_model.get_note(note_id)
        assert (note.x, note.y, note.width, note.height) == (100, 120, 300, 280)

    def test_hide_and_show(self, stiky_app):
        note_id = stiky_app.create_new_note()
        window = stiky_app.windows.get(note_id)
        stiky_app.hide_note(note_id)
        assert not window.isVisible()
        assert stiky_app.note_model.get_note(note_id).is_visible is False
        stiky_app.show_all_notes()
        assert window.isVisible()
        assert stiky_app.note_model.get_note(note_id).is_visible is True

    def test_new_notes_cascade(self, stiky_app):
        first = stiky_app.note_model.get_note(stiky_app.create_new_note())
        second = stiky_app.note_model.get_note(stiky_app.create_new_note())
        assert (second.x, second.y) != (first.x, first.y)

    def test_delete_empty_note_without_confirmation(self, stiky_app):
        note_id = stiky_app.create_new_note()
        stiky_app.delete_note(note_id)
        assert stiky_app.note_model.get_note(note_id) is None
        assert stiky_app.windows.get(note_id) is None

    def test_rich_text_is_saved_from_window(self, stiky_app):
        from PyQt6.QtCore import QMetaObject, QObject

        note_id = stiky_app.create_new_note()
        window = stiky_app.windows.get(note_id)
        body = window.findChild(QObject, "body")
        body.setProperty("text", "<p>Ciao <b>mondo</b></p>")
        QMetaObject.invokeMethod(window, "flush")
        note = stiky_app.note_model.get_note(note_id)
        assert note.content == "Ciao mondo"
        assert "font-weight" in note.rich_content and "mondo" in note.rich_content

    def test_legacy_plain_note_is_shown_as_html(self, stiky_app):
        from PyQt6.QtCore import QObject

        note = stiky_app.note_model.add_note(content="Riga 1\nRiga 2")
        window = stiky_app.windows.open(note)
        body = window.findChild(QObject, "body")
        assert body.property("length") == len("Riga 1\nRiga 2")

    def test_format_bold_via_window_document(self, stiky_app):
        from PyQt6.QtGui import QFont, QTextCursor

        note_id = stiky_app.create_new_note()
        doc = stiky_app.windows.document(note_id)
        QTextCursor(doc).insertText("uno due")
        stiky_app.format_text(note_id, "bold", 0, 3, 3)
        cursor = QTextCursor(doc)
        cursor.setPosition(1)
        assert cursor.charFormat().fontWeight() == QFont.Weight.Bold

    def test_text_menu_copy_and_paste(self, stiky_app):
        """Clic destro sul testo: le voci scelte agiscono sul TextEdit."""
        from PyQt6.QtCore import Q_ARG, QMetaObject, QObject
        from PyQt6.QtWidgets import QApplication, QMenu

        note_id = stiky_app.create_new_note()
        window = stiky_app.windows.get(note_id)
        body = window.findChild(QObject, "body")
        body.setProperty("text", "<p>uno due</p>")
        QMetaObject.invokeMethod(body, "select", Q_ARG(int, 0), Q_ARG(int, 3))

        menus = []

        def choose(label):
            def fake_exec(menu, *args):
                entries = {a.text(): a for a in menu.actions()}
                menus.append({t: a.isEnabled() for t, a in entries.items() if t})
                return entries[label]
            return fake_exec

        QApplication.clipboard().clear()
        with patch.object(QMenu, "exec", choose("Copia")):
            QMetaObject.invokeMethod(window, "showTextMenu")
        assert QApplication.clipboard().text() == "uno"
        assert menus[0]["Copia"] and menus[0]["Taglia"] and menus[0]["Incolla"] is False

        body.setProperty("cursorPosition", body.property("length"))
        with patch.object(QMenu, "exec", choose("Incolla")):
            QMetaObject.invokeMethod(window, "showTextMenu")
        assert body.property("length") == len("uno dueuno")
        assert menus[1]["Copia"] is False and menus[1]["Incolla"]

    def test_text_menu_format_entry(self, stiky_app):
        from PyQt6.QtCore import Q_ARG, QMetaObject, QObject
        from PyQt6.QtGui import QFont, QTextCursor
        from PyQt6.QtWidgets import QMenu

        note_id = stiky_app.create_new_note()
        window = stiky_app.windows.get(note_id)
        body = window.findChild(QObject, "body")
        body.setProperty("text", "<p>uno due</p>")
        QMetaObject.invokeMethod(body, "select", Q_ARG(int, 4), Q_ARG(int, 7))

        def fake_exec(menu, *args):
            fmt = [a for a in menu.actions() if a.text() == "Formato"][0].menu()
            return [a for a in fmt.actions() if a.text() == "Grassetto"][0]

        with patch.object(QMenu, "exec", fake_exec):
            QMetaObject.invokeMethod(window, "showTextMenu")
        cursor = QTextCursor(stiky_app.windows.document(note_id))
        cursor.setPosition(5)
        assert cursor.charFormat().fontWeight() == QFont.Weight.Bold

    def test_due_reminder_fires(self, stiky_app):
        note_id = stiky_app.create_new_note()
        stiky_app.hide_note(note_id)
        stiky_app.note_controller.update_note(note_id, reminder="2020-01-01T09:00:00+01:00")
        with patch.object(stiky_app.tray_manager, "notify") as notify:
            stiky_app.check_reminders()
        note = stiky_app.note_model.get_note(note_id)
        assert note.reminder is None
        assert note.is_visible is True
        notify.assert_called_once()
        assert stiky_app.windows.get(note_id).property("reminderText") == ""

    def test_future_reminder_shows_label(self, stiky_app):
        from kde_plasma_stiky_notes.core import reminders

        note_id = stiky_app.create_new_note()
        when = reminders.serialize(reminders.now() + reminders.timedelta(days=30))
        stiky_app.note_controller.update_note(note_id, reminder=when)
        stiky_app.check_reminders()
        assert stiky_app.note_model.get_note(note_id).reminder == when
        assert stiky_app.windows.get(note_id).property("reminderText") != ""

    def test_desktop_choice_runs_kwin_script(self, stiky_app):
        from PyQt6.QtCore import QCoreApplication, QEventLoop, QTimer

        note_id = stiky_app.create_new_note()
        with patch("kde_plasma_stiky_notes.main.kwin_desktops") as kd:
            kd.available.return_value = True
            kd.token_for.side_effect = lambda nid: "token-" + nid
            stiky_app._set_desktop(note_id, True, -1)
            window = stiky_app.windows.get(note_id)
            assert window.property("captionOverride") == "token-" + note_id
            loop = QEventLoop()
            QTimer.singleShot(800, loop.quit)
            loop.exec()
            kd.apply.assert_called_once_with([("token-" + note_id, True, -1)])
            assert window.property("captionOverride") == ""
        note = stiky_app.note_model.get_note(note_id)
        assert (note.all_desktops, note.desktop) == (True, -1)
        assert QCoreApplication.instance() is not None


# ===== Formattazione del testo =====


class TestTextFormat:
    @pytest.fixture
    def doc(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtGui import QTextCursor, QTextDocument

        _qapp()
        d = QTextDocument()
        QTextCursor(d).insertText("prima riga\nseconda riga")
        return d

    @staticmethod
    def _fmt(doc, pos):
        from PyQt6.QtGui import QTextCursor

        c = QTextCursor(doc)
        c.setPosition(pos)
        return c.charFormat()

    def test_bold_toggles(self, doc):
        from PyQt6.QtGui import QFont

        from kde_plasma_stiky_notes.ui.text_format import apply_format

        apply_format(doc, "bold", 0, 5, 5)
        assert self._fmt(doc, 2).fontWeight() == QFont.Weight.Bold
        apply_format(doc, "bold", 0, 5, 5)
        assert self._fmt(doc, 2).fontWeight() != QFont.Weight.Bold

    def test_without_selection_formats_word(self, doc):
        from kde_plasma_stiky_notes.ui.text_format import apply_format

        apply_format(doc, "italic", 2, 2, 2)
        assert self._fmt(doc, 3).fontItalic() is True
        assert self._fmt(doc, 9).fontItalic() is False

    def test_underline_strike_and_clear(self, doc):
        from kde_plasma_stiky_notes.ui.text_format import apply_format

        apply_format(doc, "underline", 0, 5, 5)
        apply_format(doc, "strike", 0, 5, 5)
        assert self._fmt(doc, 2).fontUnderline() and self._fmt(doc, 2).fontStrikeOut()
        apply_format(doc, "clear", 0, 5, 5)
        assert not self._fmt(doc, 2).fontUnderline()
        assert not self._fmt(doc, 2).fontStrikeOut()

    def test_lists_toggle_and_switch(self, doc):
        from PyQt6.QtGui import QTextListFormat

        from kde_plasma_stiky_notes.ui.text_format import apply_format

        apply_format(doc, "bullet", 0, 15, 15)
        first, second = doc.begin(), doc.begin().next()
        assert first.textList() is not None and second.textList() is not None
        assert first.textList().format().style() == QTextListFormat.Style.ListDisc
        apply_format(doc, "numbered", 0, 15, 15)
        assert doc.begin().textList().format().style() == QTextListFormat.Style.ListDecimal
        apply_format(doc, "numbered", 0, 15, 15)
        assert doc.begin().textList() is None and doc.begin().next().textList() is None

    def test_unknown_action(self, doc):
        from kde_plasma_stiky_notes.ui.text_format import apply_format

        with pytest.raises(ValueError):
            apply_format(doc, "blink", 0, 1, 1)

    def test_plain_to_html(self):
        from kde_plasma_stiky_notes.ui.text_format import plain_to_html

        assert plain_to_html("") == ""
        out = plain_to_html("a < b\n\nfine")
        assert "a &lt; b" in out and out.count("<p>") == 3


# ===== Promemoria =====


class TestReminders:
    def test_parse_and_due(self):
        from datetime import datetime, timezone

        from kde_plasma_stiky_notes.core import reminders

        at = datetime(2026, 11, 5, 12, 0, tzinfo=timezone.utc)
        assert reminders.parse(None) is None
        assert reminders.parse("non una data") is None
        assert reminders.is_due("2026-11-05T11:59:00+00:00", at) is True
        assert reminders.is_due("2026-11-05T12:01:00+00:00", at) is False
        assert reminders.is_due(None, at) is False

    def test_serialize_roundtrip(self):
        from kde_plasma_stiky_notes.core import reminders

        when = reminders.now().replace(second=42)
        text = reminders.serialize(when)
        assert reminders.parse(text) == when.replace(second=0, microsecond=0)

    def test_short_label(self):
        from datetime import timedelta

        from kde_plasma_stiky_notes.core import reminders

        at = reminders.now().replace(hour=10, minute=0)
        today = at.replace(hour=14, minute=30)
        assert reminders.short_label(reminders.serialize(today), at) == "14:30"
        in_two_days = reminders.short_label(reminders.serialize(today + timedelta(days=2)), at)
        assert in_two_days.endswith("14:30") and len(in_two_days.split()) == 2
        far = reminders.short_label(reminders.serialize(today + timedelta(days=40)), at)
        assert "/" in far
        assert reminders.short_label(None) == ""

    def test_default_time_is_rounded_future(self):
        from kde_plasma_stiky_notes.core import reminders

        at = reminders.now().replace(hour=9, minute=7)
        proposed = reminders.default_time(at)
        assert proposed > at and proposed.minute % 15 == 0 and proposed.second == 0


class TestReminderDialog:
    """La finestra del promemoria, guidata simulando la tastiera."""

    @staticmethod
    def _run(interact):
        from PyQt6.QtWidgets import QDateEdit, QDialog, QTimeEdit

        from kde_plasma_stiky_notes.ui import reminder_dialog

        _qapp()

        def fake_exec(dialog):
            ok = interact(dialog, dialog.findChild(QDateEdit), dialog.findChild(QTimeEdit))
            return QDialog.DialogCode.Accepted if ok else QDialog.DialogCode.Rejected

        with patch.object(QDialog, "exec", fake_exec):
            return reminder_dialog.ask_reminder("Spesa", None)

    def test_hour_can_be_typed(self):
        from PyQt6.QtCore import QDate, Qt
        from PyQt6.QtTest import QTest
        from PyQt6.QtWidgets import QTimeEdit

        from kde_plasma_stiky_notes.ui import reminder_dialog

        tomorrow = QDate.currentDate().addDays(1)

        def interact(dialog, date_edit, time_edit):
            date_edit.setDate(tomorrow)
            time_edit.setSelectedSection(QTimeEdit.Section.HourSection)
            QTest.keyClicks(time_edit, "07")
            QTest.keyClick(time_edit, Qt.Key.Key_Right)
            time_edit.setSelectedSection(QTimeEdit.Section.MinuteSection)
            QTest.keyClicks(time_edit, "45")
            return True

        action, when = self._run(interact)
        assert action == reminder_dialog.SET
        assert (when.year, when.month, when.day) == (tomorrow.year(), tomorrow.month(), tomorrow.day())
        assert (when.hour, when.minute) == (7, 45)
        assert when.tzinfo is not None

    def test_past_time_disables_ok(self):
        from PyQt6.QtCore import QDate
        from PyQt6.QtWidgets import QDialogButtonBox, QLabel

        seen = {}

        def interact(dialog, date_edit, time_edit):
            ok = dialog.findChild(QDialogButtonBox).button(QDialogButtonBox.StandardButton.Ok)
            warning = [w for w in dialog.findChildren(QLabel) if "passato" in w.text()][0]
            seen["future"] = (ok.isEnabled(), warning.isHidden())
            date_edit.setDate(QDate.currentDate().addDays(-1))
            seen["past"] = (ok.isEnabled(), warning.isHidden())
            return False

        self._run(interact)
        assert seen["future"] == (True, True)
        assert seen["past"] == (False, False)
