# Stiky-notes

Note adesive (post-it) sul desktop di KDE Plasma, nello spirito del vecchio
KNotes: ogni nota è una piccola finestra colorata che resta dove la metti.
Scritta in Python con PyQt6 e Qt Quick (QML).

## Funzionalità

- **Una finestra per nota**, senza bordi, del colore della nota
- Si **sposta** trascinando la barra superiore e si **ridimensiona** dall'angolo
  in basso a destra
- **Titolo** (doppio clic sulla barra) e testo **formattato**: grassetto,
  corsivo, sottolineato, barrato, elenchi puntati e numerati (barra in basso,
  Ctrl+B/I/U)
- **Menu del testo** con il clic destro: taglia, copia, incolla, annulla,
  seleziona tutto, formato
- **Promemoria** con notifica di sistema (⏰ nella barra della nota)
- **Desktop virtuali**: ogni nota su un desktop scelto o su tutti
- **Menu della nota** (⋮ o clic destro sulla barra): nuova nota, rinomina,
  12 colori, sempre in primo piano, desktop, promemoria, nascondi, elimina
- **Salvataggio automatico** di testo, titolo, posizione e dimensioni: al
  riavvio ogni nota riappare dov'era
- **Vassoio di sistema**: clic per richiamare tutte le note in primo piano,
  clic centrale per una nuova nota, menu con l'elenco delle note
- **Avvio automatico** al login (disattivabile dal vassoio)
- **Istanza singola**: rilanciare l'app (anche con `--new`) agisce sull'istanza
  già aperta tramite D-Bus

### Wayland

Wayland non permette alle applicazioni di decidere la posizione delle proprie
finestre: le note verrebbero ricollocate dal compositor a ogni avvio. Per
questo, in una sessione Wayland, Stiky-notes usa automaticamente XWayland e
le note tornano esattamente al loro posto. Per usare Wayland nativo (le note
mantengono le dimensioni ma non la posizione) avviare con
`STIKY_NOTES_WAYLAND=1`.

## Requisiti

- Python ≥ 3.9
- PyQt6 (QtQml, QtQuick, QtDBus), moduli QML QtQuick e QtQuick.Window
- Plugin di piattaforma Qt `xcb` (pacchetto `qt6-qpa-plugins`)

## Struttura del progetto

```
Stiky-notes/
├── src/kde_plasma_stiky_notes/
│   ├── main.py                 # Avvio e coordinamento (bridge "stikyApp")
│   ├── core/
│   │   ├── note_model.py       # NoteData e persistenza (QSettings)
│   │   ├── note_controller.py  # Operazioni sulle note, colori
│   │   └── reminders.py        # Date dei promemoria
│   ├── ui/
│   │   ├── note_windows.py     # Una finestra QML per nota
│   │   ├── text_format.py      # Grassetto, corsivo, elenchi…
│   │   ├── reminder_dialog.py  # Scelta data/ora del promemoria
│   │   └── tray_manager.py     # Icona e menu nel vassoio
│   ├── platform/
│   │   ├── single_instance.py  # Istanza singola via D-Bus
│   │   ├── kwin_desktops.py    # Desktop virtuali via script KWin
│   │   └── autostart.py        # Avvio automatico XDG
│   ├── icons/                  # Icona (SVG)
│   └── qml/
│       ├── NoteWindow.qml      # Il post-it
│       └── HeaderButton.qml
├── tools/render_icons.py       # Genera le PNG dell'icona
├── tests/                      # Test (pytest)
├── debian/                     # Packaging Debian
└── docs/                       # Guida utente e di sviluppo
```

## Avvio

```bash
pip install -e .
```

```bash
python -m kde_plasma_stiky_notes
```

Opzioni: `--new` crea una nota, `--show-all` mostra tutte le note,
`--autostart` (usata al login) mostra solo le note lasciate visibili.

## Test

```bash
QT_QPA_PLATFORM=offscreen python -m pytest
```

## Pacchetto Debian

```bash
python3 build_deb_simple.py
```

## Licenza

GPL-3.0-or-later — vedi file [LICENSE](LICENSE).
