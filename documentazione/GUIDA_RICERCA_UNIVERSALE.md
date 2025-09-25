# 🔍 Guida alla Ricerca Universale

## Panoramica
La funzionalità di ricerca universale permette di cercare testo in tutte le finestre dell'applicazione Jira Timer Tracker, proprio come in Visual Studio Code.

## 🎯 Come Utilizzare la Ricerca

### Attivazione della Ricerca
- **Ctrl+F**: Apre la barra di ricerca nella finestra attiva
- La barra di ricerca apparirà nella parte superiore della finestra

### Navigazione nei Risultati
- **F3**: Vai al prossimo risultato
- **Shift+F3**: Vai al risultato precedente
- **Esc**: Chiudi la barra di ricerca

### Opzioni di Ricerca
- **🔤 Case Sensitive**: Attiva/disattiva la ricerca sensibile alle maiuscole
- **🔤 Whole Word**: Cerca solo parole intere (non parti di parole)

## 📍 Finestre con Ricerca Integrata

### 📝 Gestione Note
- **Tabella delle note**: Cerca nelle colonne visibili della tabella
- **Editor del contenuto**: Cerca nel testo del contenuto della nota
- **Campo titolo**: Cerca nei titoli delle note
- **Campo JIRA key**: Cerca nelle chiavi JIRA associate
- **Campo tags**: Cerca nei tag delle note

### 🎫 Dettaglio JIRA
- **Descrizione JIRA**: Cerca nella descrizione dell'issue
- **Commenti JIRA**: Cerca in tutti i commenti dell'issue
- **Note personali**: Cerca nelle note personali aggiunte all'issue
- **Campi dettaglio**: Cerca in tutti i campi informativi dell'issue

### 📎 Allegati
- **Lista allegati**: Cerca nei nomi e nelle descrizioni degli allegati
- **Metadati**: Cerca nelle informazioni degli allegati

### 🏠 Finestra Principale
- **Griglia JIRA**: Cerca nelle colonne della tabella JIRA
- **Cronologia tempo**: Cerca nella cronologia delle attività temporali

## 💡 Suggerimenti per un Utilizzo Efficace

### Ricerca Rapida
1. Premi **Ctrl+F** in qualsiasi finestra
2. Inizia a digitare: i risultati appariranno in tempo reale
3. Usa **F3/Shift+F3** per navigare rapidamente tra i risultati

### Ricerca Precisa
- Attiva **Case Sensitive** per distinguere maiuscole/minuscole
- Attiva **Whole Word** per cercare parole esatte
- Combina entrambe le opzioni per ricerche molto specifiche

### Esempi di Utilizzo

#### Cercare un Issue Specifico
1. Apri la finestra principale
2. Ctrl+F → digita "PROJ-1234"
3. La griglia evidenzierà tutti i match

#### Cercare in Note e Commenti
1. Apri il dettaglio di un issue
2. Ctrl+F → digita "bug"
3. Naviga tra descrizione, commenti e note personali

#### Cercare Allegati
1. Apri la finestra allegati
2. Ctrl+F → digita "documento"
3. Trova rapidamente allegati specifici

## 🎨 Interfaccia della Ricerca

La barra di ricerca include:
- **Campo di input**: Inserisci il testo da cercare
- **Contatore risultati**: Mostra "X di Y" risultati trovati
- **Pulsanti navigazione**: ⬆️ (precedente) e ⬇️ (successivo)
- **Opzioni**: Checkbox per Case Sensitive e Whole Word
- **Pulsante chiusura**: ❌ per chiudere la ricerca

## 🔧 Comportamento Tecnico

### Ricerca in Tempo Reale
- I risultati si aggiornano mentre digiti
- Nessun bisogno di premere Enter
- Evidenziazione istantanea dei match

### Gestione dei Widget
- La ricerca funziona su:
  - QTextEdit (editor di testo)
  - QListWidget (liste)
  - QTableWidget (tabelle)
  - Tutti i widget di testo personalizzati

### Persistenza della Ricerca
- La ricerca rimane attiva fino a quando non viene chiusa
- Cambiare finestra mantiene l'ultima ricerca effettuata
- Ogni finestra ha la sua istanza di ricerca indipendente

## 🚀 Vantaggi della Ricerca Universale

### Produttività
- Trova rapidamente informazioni in grandi quantità di dati
- Naviga efficientemente tra più risultati
- Interfaccia familiare simile a VS Code

### Flessibilità
- Funziona in tutte le finestre dell'applicazione
- Opzioni di ricerca personalizzabili
- Integrazione seamless con l'interfaccia esistente

### Usabilità
- Shortcut intuitivi e universali
- Feedback visivo immediato
- Comportamento consistente tra tutte le finestre

---

**Nota**: Questa funzionalità è stata implementata per migliorare significativamente l'esperienza utente nell'applicazione Jira Timer Tracker, rendendo la ricerca di informazioni rapida ed efficiente come in un moderno editor di codice.