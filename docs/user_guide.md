# Guida Utente - Stiky-notes

Stiky-notes mette dei post-it sul desktop: ogni nota è una piccola finestra
colorata che resta dove la lasci, anche dopo un riavvio.

## Installazione

Pacchetto Debian/Ubuntu (generato con `build_deb_simple.py`):

```bash
sudo apt install ./stiky-notes_0.3.1-1_all.deb
```

Oppure da sorgente: `pip install -e .`

## Avvio

Avvia **Stiky-notes** dal menu delle applicazioni (o con `stiky-notes`).
Compaiono le tue note; se non ne hai ancora, ne viene creata una.
L'icona gialla nel vassoio di sistema indica che l'app è attiva.

Al login l'app parte da sola (si disattiva da *Avvio automatico* nel menu del
vassoio) e mostra solo le note che avevi lasciato visibili.

## Usare una nota

| Azione | Come |
|---|---|
| Scrivere | Clic nell'area della nota e digita |
| Spostare | Trascina la barra superiore |
| Ridimensionare | Trascina l'angolo in basso a destra |
| Dare un titolo | Doppio clic sulla barra (Invio conferma, Esc annulla) |
| Nuova nota | Pulsante **+**, oppure Ctrl+N |
| Menu della nota | Pulsante **⋮** o clic destro sulla barra |
| Nascondere | Pulsante **✕** (la nota non viene eliminata) |

## Formattare il testo

Quando una nota è attiva compare in basso una barra di formattazione:

| Pulsante | Effetto | Scorciatoia |
|---|---|---|
| **B** | Grassetto | Ctrl+B |
| *I* | Corsivo | Ctrl+I |
| U | Sottolineato | Ctrl+U |
| S | Barrato | |
| • | Elenco puntato (di nuovo per toglierlo) | |
| 1. | Elenco numerato (di nuovo per toglierlo) | |
| ⌫ | Rimuove la formattazione | |

Si applica al testo selezionato; senza selezione, alla parola sotto il
cursore (gli elenchi al paragrafo). Ctrl+Z annulla.

Dal menu della nota:

- **Nuova nota**
- **Rinomina…** — modifica il titolo
- **Colore** — 12 colori
- **Sempre in primo piano** — la nota resta sopra le altre finestre
- **Desktop** — *Tutti i desktop* oppure un desktop virtuale specifico
- **Promemoria…** — data e ora in cui ricevere un avviso
- **Nascondi**
- **Elimina…** — chiede conferma se la nota contiene del testo

Tutto viene salvato da solo: testo, titolo, colore, posizione e dimensioni.

## Promemoria

Dal menu della nota scegli **Promemoria…** e imposta data e ora. Nella barra
della nota compare ⏰ con l'orario (clic per modificarlo o rimuoverlo).
Alla scadenza arriva una notifica di sistema e la nota viene mostrata in primo
piano, anche se era nascosta; cliccando la notifica la nota torna in vista.
Se l'app era chiusa, i promemoria scaduti scattano al successivo avvio.

## Desktop virtuali

Dal menu della nota, **Desktop → Tutti i desktop** la mostra su ogni desktop
virtuale; scegliendo un desktop specifico la nota resta solo lì. La scelta
viene ricordata. Richiede KWin (KDE Plasma).

## Vassoio di sistema

- **Clic**: mostra tutte le note e le porta in primo piano (utile quando sono
  coperte da altre finestre)
- **Clic centrale**: nuova nota
- **Clic destro**: menu con *Nuova nota*, *Note* (elenco: clic per richiamarne
  una, anche se nascosta), *Mostra tutte le note*, *Nascondi tutte le note*,
  *Avvio automatico* ed *Esci*

Nascondere tutte le note non chiude l'app: per uscire usa *Esci*.

## Sessioni Wayland

Su Wayland le applicazioni non possono scegliere dove aprire le proprie
finestre. Per far riapparire ogni nota al suo posto, Stiky-notes usa
automaticamente XWayland. Se preferisci Wayland nativo (le note mantengono
le dimensioni ma è KWin a deciderne la posizione):

```bash
STIKY_NOTES_WAYLAND=1 stiky-notes
```

## Dove sono salvate le note

`~/.config/StikyNotes/NoteModel.conf`. Una copia di questo file è un backup
completo; eliminarlo cancella tutte le note.

## Risoluzione problemi

**Le note non tornano al loro posto** — verifica di non aver impostato
`STIKY_NOTES_WAYLAND=1` o `QT_QPA_PLATFORM=wayland`.

**Le note sono coperte dalle altre finestre** — clic sull'icona nel vassoio,
oppure attiva *Sempre in primo piano* sulle note che vuoi tenere in vista.

**"Un'altra istanza possiede il nome D-Bus ma non risponde"** — un processo
Stiky-notes è bloccato: terminalo (`pkill -f kde_plasma_stiky_notes`) e riavvia.

**Una nota non compare dopo il riavvio** — se i suoi dati sono corrotti viene
saltata e il motivo è stampato sul terminale (`[NoteModel] Nota ... ignorata`).
