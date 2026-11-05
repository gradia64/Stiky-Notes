# Guida allo Sviluppo - Stiky-notes

## Architettura

```
NoteWindow.qml (una per nota) ──slot──▶ StikyNotesApp (main.py, "stikyApp")
        ▲                                   │
        │ proprietà (colore, keepAbove)     ├──▶ NoteController ──▶ NoteModel (QSettings)
        └──── NoteWindowManager ◀───────────┤
              (ui/note_windows.py)          ├──▶ TrayManager (ui/tray_manager.py)
                                            └──◀ SingleInstanceService (D-Bus)
```

| Componente | Responsabilità | File |
|---|---|---|
| `NoteData` / `NoteModel` | Schema della nota, caricamento e salvataggio su QSettings | `core/note_model.py` |
| `NoteController` | Crea/aggiorna/elimina/fissa note ed emette `note_created`, `note_updated`, `note_deleted`; palette colori; etichette | `core/note_controller.py` |
| `StikyNotesApp` | Coordina tutto; slot chiamati dal QML; menu della nota; posizionamento a cascata | `main.py` |
| `NoteWindowManager` | Crea una finestra da `NoteWindow.qml` per ogni nota, la mostra/nasconde/distrugge | `ui/note_windows.py` |
| `TrayManager` | Icona e menu del vassoio, elenco delle note | `ui/tray_manager.py` |
| `SingleInstanceService` | Nome D-Bus `org.kde.StikyNotes`, metodi `NewNote`/`ShowAll` | `platform/single_instance.py` |
| `autostart` | Attiva/disattiva l'avvio automatico XDG | `platform/autostart.py` |
| `text_format` | Formattazione sul QTextDocument del TextEdit (grassetto, elenchi…) | `ui/text_format.py` |
| `reminders` / `reminder_dialog` | Date dei promemoria; finestra di scelta | `core/reminders.py`, `ui/reminder_dialog.py` |
| `kwin_desktops` | Desktop virtuali tramite script KWin caricati via D-Bus | `platform/kwin_desktops.py` |

### Flusso di una modifica

- **Testo e titolo** nascono nella finestra: `NoteWindow.qml` li salva con un
  debounce di 500 ms (e subito quando perde il focus o viene chiusa) tramite
  `stikyApp.update_note_content/title` → controller → modello. Il controller
  emette `note_updated` e il vassoio aggiorna l'elenco.
- **Colore e "sempre in primo piano"** nascono nel menu Python: il controller
  aggiorna il modello e `StikyNotesApp` imposta le proprietà `noteColor` e
  `keepAbove` sulla finestra.
- **Posizione e dimensioni** arrivano dalla finestra con un debounce di
  600 ms (`update_note_geometry`) e vanno direttamente al modello, senza
  segnali: non cambiano nulla per il resto dell'interfaccia.

### Testo formattato

Il `TextEdit` della nota usa `TextEdit.RichText`. A ogni salvataggio il QML
invia sia il testo semplice (`content`, usato per le etichette) sia l'HTML
(`rich_content`). Le note salvate prima della 0.3 hanno solo `content`, che
viene convertito al volo con `text_format.plain_to_html`.

La formattazione è applicata da Python (`text_format.apply_format`) sul
`QTextDocument` del TextEdit, recuperato con `NoteWindowManager.document()`:
così il TextEdit si aggiorna da solo e Ctrl+Z annulla anche la formattazione.

### Promemoria

`NoteData.reminder` è una data ISO 8601 con fuso orario. `StikyNotesApp`
controlla le scadenze ogni 15 secondi (e all'avvio): un promemoria scaduto
viene cancellato, la nota mostrata e inviata una notifica con
`QSystemTrayIcon.showMessage`.

### Desktop virtuali

Né Wayland né KWin (per le finestre XWayland, la richiesta EWMH
`_NET_WM_DESKTOP` viene ignorata) permettono a un'app di spostare le proprie
finestre tra i desktop. `kwin_desktops` carica quindi via D-Bus un breve
script KWin che imposta `desktops`/`onAllDesktops`. Per riconoscere la
finestra, la nota riceve per ~0,6 s un titolo temporaneo univoco
(`captionOverride` in `NoteWindow.qml`). La scelta è salvata in
`NoteData.desktop` / `all_desktops` e riapplicata all'avvio e quando una nota
nascosta viene mostrata.

### Icona

Sorgenti in `src/kde_plasma_stiky_notes/icons/` (`stiky-notes.svg` e la
variante semplificata `stiky-notes-small.svg` per 16–24 px). Dopo una
modifica, rigenera le PNG con `python3 tools/render_icons.py`.

### Spostamento e ridimensionamento

Le finestre sono senza bordi (`Qt.FramelessWindowHint`). Lo spostamento usa
`startSystemMove()` (avviato solo dopo qualche pixel di trascinamento, così
clic e doppio clic sulla barra restano disponibili) e il ridimensionamento
`startSystemResize()`: è il window manager a gestire l'operazione, quindi
funzionano sia su X11 che su Wayland.

### Wayland e posizioni

Su Wayland un client non può leggere né impostare la posizione globale delle
proprie finestre. `main._choose_platform()` imposta quindi
`QT_QPA_PLATFORM=xcb` (XWayland) nelle sessioni Wayland, salvo
`STIKY_NOTES_WAYLAND=1` o un `QT_QPA_PLATFORM` già impostato. Su Wayland
nativo `update_note_geometry` salva solo le dimensioni, per non sovrascrivere
le posizioni salvate con valori senza significato.

### Persistenza

Ogni nota è salvata come dizionario sotto la chiave `note_<uuid>` in
`~/.config/StikyNotes/NoteModel.conf`. `NoteData.from_dict` ignora le chiavi
sconosciute e usa i valori predefiniti per quelle mancanti: aggiungere un
campo a `NoteData` non richiede migrazioni. `is_pinned` significa "sempre in
primo piano"; `is_visible` indica se la nota è mostrata o nascosta. `rich_content`
è l'HTML del testo, `reminder` il promemoria, `desktop`/`all_desktops` il
desktop virtuale. Alcuni campi (font, priorità, tag…) non sono ancora usati.

### Chiusura

All'uscita (`aboutToQuit`) ogni finestra salva le modifiche pendenti
(`flush`), poi `main()` blocca i segnali Python, distrugge le finestre, sgancia
`stikyApp` dal contesto QML e distrugge il motore QML mentre `QApplication` è
ancora vivo. Serve a evitare SIGABRT in uscita con PyQt6.

## Ambiente di sviluppo

```bash
python3 -m venv venv && source venv/bin/activate
pip install -e . pytest
```

Per provare l'app senza toccare le proprie note:

```bash
XDG_CONFIG_HOME=/tmp/stiky-test dbus-run-session -- python -m kde_plasma_stiky_notes
```

## Test

```bash
QT_QPA_PLATFORM=offscreen python -m pytest -v
```

I test simulano QSettings con `unittest.mock.patch` per non scrivere su disco;
quelli di `StikyNotesApp` creano vere finestre QML sulla piattaforma
`offscreen`; quelli dell'avvio automatico usano `XDG_CONFIG_HOME`/
`XDG_CONFIG_DIRS` in una cartella temporanea.

## Pacchetto Debian

- `build_deb_simple.py`: costruisce direttamente il `.deb` con `dpkg-deb`
  (versione indicata nello script).
- `debian/`: packaging standard con `dh` + pybuild (`dpkg-buildpackage -us -uc -b`).

Il pacchetto installa il file `.desktop`, l'autostart in `/etc/xdg/autostart`
(con `--autostart`), le icone e il file di attivazione D-Bus
`org.kde.StikyNotes.service`.

## Aggiungere funzionalità

- **Nuovo campo nota**: aggiungilo a `NoteData` con un valore predefinito.
- **Nuova voce nel menu della nota**: aggiungila in
  `StikyNotesApp.show_note_menu`; se cambia l'aspetto della finestra, esponi
  una proprietà in `NoteWindow.qml` e impostala in `_on_note_updated`.
- **Nuova azione dalla finestra**: aggiungi un `@pyqtSlot` a `StikyNotesApp`
  e richiamalo da `NoteWindow.qml`.
- **Nuova voce nel vassoio**: aggiungi un `QAction` in
  `TrayManager._build_menu` e un segnale collegato in `StikyNotesApp`.
- **Nuovo comando D-Bus**: aggiungi uno slot a `SingleInstanceService`.
