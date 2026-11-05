# Changelog - Stiky-notes

Tutte le modifiche significative di questo progetto sono documentate in questo file.

Il formato è basato su [Keep a Changelog](https://keepachangelog.com/it/1.0.0/),
e questo progetto aderisce a [Semantic Versioning](https://semver.org/lang/it/).

## [0.3.0] - 2026-11-05

### Aggiunto
- Formattazione del testo: grassetto, corsivo, sottolineato, barrato, elenchi
  puntati e numerati, rimozione della formattazione. Barra in basso quando la
  nota è attiva e scorciatoie Ctrl+B / Ctrl+I / Ctrl+U; annullabile con Ctrl+Z
- Promemoria: data e ora dal menu della nota (o dal badge ⏰ nella barra);
  alla scadenza notifica di sistema e nota portata in primo piano. I
  promemoria scaduti mentre l'app era chiusa scattano all'avvio
- Desktop virtuali: dal menu della nota, "Tutti i desktop" o un desktop
  specifico, ricordato tra un avvio e l'altro (tramite script KWin)
- Nuova icona (SVG scalabile + PNG, variante semplificata per 16–24 px),
  usata anche nel vassoio e per le finestre; `tools/render_icons.py` rigenera
  le PNG

### Modificato
- Il testo delle note è salvato anche in HTML (`rich_content`); `content`
  resta il testo semplice. Le note delle versioni precedenti si aprono senza
  conversioni

## [0.2.0] - 2026-11-05

### Modificato
- Ogni nota è un post-it a sé sul desktop (`qml/NoteWindow.qml`): finestra
  senza bordi del colore della nota, spostabile dalla barra superiore e
  ridimensionabile dall'angolo; sostituisce la finestra con l'elenco delle note
- Clic sull'icona del vassoio: mostra tutte le note in primo piano (prima creava
  una nota); il clic centrale crea una nuova nota
- Nelle sessioni Wayland l'app usa XWayland per poter ripristinare la posizione
  delle note (`STIKY_NOTES_WAYLAND=1` per Wayland nativo)
- Nuove note di 250×250, posizionate a cascata dall'angolo in alto a destra

### Aggiunto
- Menu della nota: nuova nota, rinomina, colore, sempre in primo piano,
  nascondi, elimina (con conferma se la nota non è vuota)
- Salvataggio di posizione e dimensioni di ogni nota
- Elenco delle note nel menu del vassoio, con il loro colore
- Opzione `--autostart`: al login riappaiono solo le note lasciate visibili;
  un avvio manuale mostra tutte le note (o ne crea una se non ce ne sono)
- Scorciatoia Ctrl+N per una nuova nota

### Rimosso
- Dipendenze dai moduli QML QtQuick.Controls e QtQuick.Layouts

## [0.1.1] - 2026-11-05

### Aggiunto
- Istanza singola via D-Bus (`org.kde.StikyNotes`, metodi `NewNote` e `ShowAll`):
  un secondo avvio inoltra la richiesta all'istanza attiva
- Voce "Avvio automatico" del vassoio funzionante (XDG autostart)

### Rimosso
- Codice non utilizzato dall'applicazione: `platform/kde_integration.py`,
  `platform/dbus_service.py`, `platform/desktop_entry.py`, `ui/settings_dialog.py`,
  `debian/pybuild`
- Dal controller: pattern Command/undo, formattazione, duplicazione, priorità,
  promemoria, blocco, spostamento/ridimensionamento, colori recenti, ricerca e filtri
  (nessuna di queste funzioni era raggiungibile dall'interfaccia)
- Dal modello: tag, ricerca, nota attiva, esposizione diretta a QML, lock di threading
- Dal vassoio: voci "Impostazioni", "Abilita toast", "Abilita suoni" e il sottomenu
  "Sistema", non collegati a nulla

### Corretto
- Perdita delle modifiche chiudendo l'editor con Esc o con un clic esterno
- Salvataggi spuri all'apertura di una nota
- `NameError` all'import di `note_model` su Python < 3.14
- Caricamento tollerante a note corrotte o a campi sconosciuti
- Ordine delle note stabile dopo il riavvio; z-index ripristinato
- Packaging Debian: Build-Depends per hatchling/pyproject, descrizione allineata

---

## [0.1.0] - 2026-11-05

### Aggiunto
- Release iniziale: lista di note con titolo, contenuto, 12 colori e pin,
  editor in finestra singola, icona nel vassoio di sistema, salvataggio automatico
