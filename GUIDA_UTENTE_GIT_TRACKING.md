# Guida Utente: Sistema di Tracking Git per Issue Jira

## 📋 Panoramica

Il **Sistema di Tracking Git** è una nuova funzionalità del Jira Timer Tracker che registra automaticamente tutte le modifiche apportate ai ticket Jira utilizzando Git come sistema di versionamento. Questo sostituisce il precedente sistema di note automatiche con una soluzione molto più potente e flessibile.

## 🎯 Cosa Fa il Sistema

### Tracking Automatico
- **Monitora automaticamente** ogni modifica ai ticket Jira (descrizione, stato, priorità, assegnatario, etc.)
- **Crea commit Git** solo quando rileva modifiche reali
- **Genera cronologia completa** di tutte le variazioni nel tempo
- **Elimina completamente** le note automatiche duplicate

### Vantaggi Principali
- ✅ **Cronologia completa** senza duplicati
- ✅ **Visualizzazione delle differenze** tra versioni 
- ✅ **Ricerca avanzata** nelle modifiche storiche
- ✅ **Backup automatico** distribuito
- ✅ **Performance ottimizzata** con compressione Git

---

## 🚀 Come Utilizzare la Funzionalità

### 1. Attivazione Automatica
Il sistema si attiva **automaticamente** quando:
- Apri un ticket Jira nell'applicazione
- Il sistema rileva modifiche nei campi principali del ticket
- Non richiede configurazione manuale

### 2. Accesso alla Cronologia

#### Pulsante Cronologia
Nella vista dettaglio di ogni ticket, troverai il pulsante **"📊 Cronologia"**:

```
[🔗 Apri in Jira] [📊 Cronologia] [🔔 Notifiche]
```

Cliccando su questo pulsante si apre la **finestra di cronologia Git**.

#### Finestra Cronologia Git
La finestra mostra:

**Pannello Sinistro - Lista Commit:**
- Lista cronologica di tutte le modifiche
- Data e ora di ogni modifica
- Descrizione automatica dei cambiamenti
- Indicatore "LATEST" per l'ultima modifica

**Pannello Destro - Dettagli:**
- Informazioni complete del commit selezionato
- Diff dettagliato delle modifiche
- Confronto "prima → dopo" per ogni campo

### 3. Esempio di Utilizzo Pratico

#### Scenario: Ticket PROJ-123 viene modificato

**Modifica 1:** Status cambiato da "To Do" a "In Progress"
```
Commit: Update PROJ-123: Status: 'To Do' → 'In Progress'
Data: 15 Gen 2024, 14:30
```

**Modifica 2:** Assegnato a John Doe
```
Commit: Update PROJ-123: Assignee: 'Unassigned' → 'John Doe'
Data: 15 Gen 2024, 15:45
```

**Modifica 3:** Priorità aumentata
```
Commit: Update PROJ-123: Priority: 'Medium' → 'High'
Data: 16 Gen 2024, 09:15
```

---

## 🔍 Funzionalità Avanzate

### Export della Cronologia
- **Pulsante "💾 Export"** nella finestra cronologia
- Salva tutta la cronologia in file di testo
- Formato leggibile per condivisione o archiviazione

### Refresh Manuale
- **Pulsante "🔄 Refresh"** per aggiornare la cronologia
- Utile se ci sono state modifiche esterne al ticket

### Ricerca e Navigazione
- **Click su qualsiasi commit** per vedere i dettagli
- **Scroll nella cronologia** per vedere modifiche passate
- **Diff dettagliati** mostrano esattamente cosa è cambiato

---

## 📊 Cosa Viene Tracciato

### Campi Monitorati
Il sistema traccia automaticamente le modifiche a:

| Campo | Descrizione |
|-------|-------------|
| **Summary** | Titolo del ticket |
| **Description** | Descrizione dettagliata |
| **Status** | Stato del workflow (To Do, In Progress, Done, etc.) |
| **Priority** | Priorità (Low, Medium, High, etc.) |
| **Assignee** | Persona assegnata al ticket |
| **Reporter** | Chi ha creato il ticket |
| **Issue Type** | Tipo di issue (Bug, Task, Story, etc.) |
| **Components** | Componenti del progetto interessati |
| **Fix Versions** | Versioni di rilascio target |
| **Labels** | Etichette associate |
| **Resolution** | Stato di risoluzione |

### Cosa NON Viene Tracciato
- ❌ **Commenti** (troppo frequenti e rumorosi)
- ❌ **Log di lavoro** (gestiti separatamente)
- ❌ **Allegati** (tracciati in altro modo)
- ❌ **Link tra issue** (gestiti separatamente)

---

## 🗂️ Struttura Tecnica (Per Utenti Avanzati)

### Directory di Tracking
Il sistema crea automaticamente:
```
progetto/
└── .jira_tracking/          # Repository Git nascosto
    ├── .git/                # Dati Git standard
    ├── README.md            # Documentazione
    └── issues/              # File dei ticket
        ├── PROJ-123.json    # Dati ticket PROJ-123
        ├── PROJ-124.json    # Dati ticket PROJ-124
        └── ...
```

### Formato File Ticket
Ogni ticket è salvato come file JSON con struttura completa:
```json
{
  "jira_key": "PROJ-123",
  "summary": "Fix login bug",
  "status": {"name": "In Progress", "id": "3"},
  "priority": {"name": "High", "id": "2"},
  "assignee": {
    "displayName": "John Doe",
    "emailAddress": "john@company.com"
  },
  "last_tracked": "2024-01-16T14:45:30.123456"
}
```

---

## 🛠️ Comandi Git Avanzati (Opzionali)

Per utenti che conoscono Git, è possibile utilizzare comandi avanzati:

### Cronologia Ticket Specifico
```bash
cd .jira_tracking
git log --oneline -- issues/PROJ-123.json
```

### Differenze tra Versioni
```bash
git show HEAD -- issues/PROJ-123.json
git diff HEAD~1 HEAD -- issues/PROJ-123.json
```

### Ricerca nelle Modifiche
```bash
# Tutte le modifiche di priorità nell'ultima settimana
git log --grep="Priority" --since="1 week ago"

# Statistiche delle modifiche per autore
git shortlog -s -n
```

### Stato Repository
```bash
# Dimensione del repository
du -sh .jira_tracking

# Numero totale di commit
git rev-list --count HEAD
```

---

## 🔧 Risoluzione Problemi

### Problema: "Git Tracking Non Disponibile"
**Causa:** Git non è installato sul sistema
**Soluzione:** 
1. Installare Git da https://git-scm.com/
2. Assicurarsi che `git` sia nel PATH di sistema
3. Riavviare l'applicazione

### Problema: "Impossibile aprire la cronologia Git"
**Causa:** Permessi insufficienti o repository corrotto
**Soluzione:**
1. Verificare permessi di scrittura nella directory del progetto
2. Se necessario, eliminare la cartella `.jira_tracking`
3. Riavviare l'applicazione (si reinizializzerà automaticamente)

### Problema: "No history found"
**Causa:** Ticket non ancora tracciato o tracking appena iniziato
**Soluzione:**
- Questo è normale per ticket nuovi
- Il tracking inizia dalla prima volta che il ticket viene aperto
- Fare alcune modifiche al ticket per vedere la cronologia

---

## 📈 Casi d'Uso Pratici

### 1. Analisi delle Modifiche
**Scenario:** Vuoi sapere quando e perché un ticket è stato riaperto
**Soluzione:** Apri la cronologia e cerca i commit con cambio di status

### 2. Audit Trail
**Scenario:** Necessità di documentare chi ha fatto cosa e quando
**Soluzione:** Esporta la cronologia completa per documentazione

### 3. Debugging Workflow
**Scenario:** Un ticket ha avuto modifiche inaspettate
**Soluzione:** Analizza i diff dettagliati per vedere esattamente cosa è cambiato

### 4. Reporting
**Scenario:** Creare report delle modifiche per il management
**Soluzione:** Utilizza i comandi Git avanzati per estrarre statistiche

---

## 🔮 Roadmap Futura

### Prossime Funzionalità
- **Dashboard Analytics:** Statistiche visive delle modifiche
- **Notifiche Intelligenti:** Alert per pattern di modifiche specifici
- **Sync Distribuito:** Condivisione cronologia tra team
- **Rollback Interface:** Ripristino versioni precedenti tramite UI
- **Webhook Integration:** Trigger automatici per modifiche esterne

### Miglioramenti Pianificati
- **Performance:** Ottimizzazioni per repository molto grandi
- **Filtri Avanzati:** Ricerca per data, autore, tipo di modifica
- **Export Formats:** Supporto per Excel, PDF, CSV
- **Mobile Support:** Visualizzazione cronologia su dispositivi mobili

---

## 🎓 Best Practices

### Per Utenti Standard
1. **Controlla regolarmente** la cronologia dei ticket importanti
2. **Usa l'export** per documentare modifiche significative  
3. **Non eliminare** la cartella `.jira_tracking`
4. **Backup regolari** del progetto (include automaticamente la cronologia)

### Per Amministratori
1. **Monitora la dimensione** del repository di tracking
2. **Configura backup** automatici della directory di progetto
3. **Documenta** l'utilizzo del sistema per il team
4. **Pianifica migrazione** dati se necessario

---

## 📞 Supporto

### Documentazione Tecnica
- `GIT_TRACKING_DOCUMENTATION.md` - Documentazione tecnica completa
- `CHANGELOG_EDITOR_IMPROVEMENTS.md` - Storia delle modifiche

### Log e Debugging
- I log dell'applicazione contengono informazioni dettagliate
- Livello di log configurabile per debugging avanzato
- File di log nella directory standard dell'applicazione

---

## 🏁 Conclusione

Il **Sistema di Tracking Git** rappresenta un significativo passo avanti nella gestione della cronologia dei ticket Jira. Offre:

- **Visibilità completa** di tutte le modifiche
- **Strumenti potenti** per analisi e ricerca  
- **Affidabilità** del sistema Git
- **Flessibilità** per usi avanzati

Il sistema è progettato per essere **trasparente** nell'uso quotidiano ma **potente** quando serve analisi dettagliata. La transizione dal vecchio sistema è **automatica** e **senza perdita** di dati esistenti.

Benvenuto nel futuro del tracking dei ticket Jira! 🚀