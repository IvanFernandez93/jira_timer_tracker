# Git-Based Issue Tracking System

## Panoramica

Il nuovo sistema di tracking delle modifiche degli issue Jira utilizza **Git** come backend per versioning e cronologia, sostituendo completamente il precedente sistema basato su database con note di log.

## Vantaggi del Sistema Git

### 🚀 **Potenza e Flessibilità**
- **Cronologia completa**: Ogni modifica è tracciata con timestamp, autore e descrizione dettagliata
- **Diff intelligenti**: Visualizzazione precisa delle modifiche tra versioni
- **Branching possibile**: Supporto futuro per branch di tracking separati
- **Rollback**: Possibilità di vedere lo stato di un issue in qualsiasi momento storico

### 🔍 **Queryability Avanzata**
- **Git Log**: `git log --oneline issues/PROJ-123.json`
- **Diff tra versioni**: `git diff HEAD~1 HEAD -- issues/PROJ-123.json`
- **Ricerca nel tempo**: `git log --since="1 week ago" --grep="Priority"`
- **Statistiche**: `git shortlog -s -n` per vedere chi ha fatto più modifiche

### 💾 **Efficienza**
- **Compressione automatica**: Git comprime la cronologia
- **Deduplicazione**: Contenuti identici vengono condivisi
- **Backup distribuito**: La cronologia è intrinsecamente distribuibile

## Architettura del Sistema

### Struttura Directory
```
project_root/
├── .jira_tracking/                 # Repository Git di tracking
│   ├── .git/                       # Dati Git
│   ├── README.md                   # Documentazione
│   ├── .gitignore                  # File da ignorare
│   └── issues/                     # Directory degli issue
│       ├── PROJ-123.json           # Dati issue PROJ-123
│       ├── PROJ-124.json           # Dati issue PROJ-124
│       └── ...
```

### Formato File Issue
Ogni issue viene salvato come file JSON con struttura completa:

```json
{
  "jira_key": "PROJ-123",
  "summary": "Fix login bug",
  "description": "Users cannot login with special characters",
  "status": {
    "name": "In Progress",
    "id": "3"
  },
  "priority": {
    "name": "High", 
    "id": "2"
  },
  "assignee": {
    "displayName": "John Doe",
    "emailAddress": "john@company.com"
  },
  "reporter": {
    "displayName": "Jane Smith",
    "emailAddress": "jane@company.com"
  },
  "issuetype": {
    "name": "Bug",
    "id": "1"
  },
  "created": "2024-01-15T10:30:00.000+0100",
  "updated": "2024-01-16T14:45:00.000+0100",
  "resolution": {
    "name": "",
    "id": ""
  },
  "labels": ["frontend", "authentication"],
  "components": [
    {"name": "Login System", "id": "123"}
  ],
  "fixVersions": [
    {"name": "v2.1.0", "id": "456"}
  ],
  "versions": [
    {"name": "v2.0.0", "id": "789"}
  ],
  "last_tracked": "2024-01-16T14:45:30.123456",
  "tracking_metadata": {
    "tracked_by": "jira-timer-tracker",
    "version": "1.0"
  }
}
```

## Funzionalità Implementate

### 1. **Tracking Automatico**
- **Rilevamento Intelligente**: Confronto hash per rilevare modifiche reali
- **Commit Automatici**: Ogni modifica genera un commit descrittivo
- **Messaggi Intelligenti**: Commit message che descrivono le modifiche specifiche

**Esempio di commit message:**
```
Update PROJ-123: Status: 'To Do' → 'In Progress'; Assignee: 'Unassigned' → 'John Doe'
```

### 2. **Interfaccia Grafica**
- **Pulsante "Cronologia"**: Accesso diretto dalla vista issue
- **Dialog Cronologia**: Visualizzazione user-friendly della cronologia Git
- **Lista Commit**: Cronologia ordinata per data
- **Diff Viewer**: Visualizzazione dettagliata delle modifiche

### 3. **Funzioni di Utilità**
- **Export**: Esportazione cronologia in formato testo
- **Ricerca**: Navigazione nella cronologia
- **Statistiche**: Informazioni sul repository di tracking

## Servizi e Componenti

### GitTrackingService
**Posizione**: `services/git_tracking_service.py`

**Responsabilità**:
- Inizializzazione repository Git
- Rilevamento e commit delle modifiche
- Query della cronologia
- Gestione dei file JSON degli issue

**Metodi Principali**:
```python
# Traccia modifiche di un issue
track_issue_changes(jira_key, issue_data) -> bool

# Ottiene cronologia di un issue  
get_issue_history(jira_key, limit=10) -> List[Dict]

# Ottiene modifiche specifiche di un commit
get_issue_changes(jira_key, commit_hash) -> Dict

# Ottiene dati attuali di un issue
get_current_issue_data(jira_key) -> Dict
```

### GitIssueHistoryDialog  
**Posizione**: `views/git_history_dialog.py`

**Funzionalità**:
- Interfaccia grafica per visualizzare cronologia
- Lista commit con informazioni dettagliate  
- Viewer per diff delle modifiche
- Funzioni di export e refresh

## Integrazione nel Controller

### JiraDetailController
**Modifiche implementate**:

1. **Inizializzazione**:
   ```python
   self.git_tracking = GitTrackingService()
   ```

2. **Tracking Automatico**:
   ```python
   def _track_issue_changes(self):
       changes_committed = self.git_tracking.track_issue_changes(
           self.jira_key, 
           self._issue_data
       )
   ```

3. **Pulsante Cronologia**:
   ```python
   def _show_git_history(self):
       dialog = GitIssueHistoryDialog(...)
       dialog.exec()
   ```

## Vantaggi Rispetto al Sistema Precedente

### ❌ **Prima (Database)**
- Note duplicate per modifiche identiche
- Cronologia limitata e non queryable  
- Nessun diff tra versioni
- Storage inefficiente
- Difficile backup e sincronizzazione

### ✅ **Ora (Git)**  
- Cronologia completa senza duplicati
- Diff intelligenti tra versioni
- Queryability avanzata con comandi Git
- Compressione automatica
- Backup e sync naturali con Git
- Possibilità di analisi avanzate

## Comandi Git Utili

### Cronologia Issue Specifico
```bash
cd .jira_tracking
git log --oneline -- issues/PROJ-123.json
```

### Diff tra Versioni
```bash
git show HEAD -- issues/PROJ-123.json
git diff HEAD~1 HEAD -- issues/PROJ-123.json
```

### Statistiche Globali
```bash
git log --since="1 month ago" --oneline | wc -l  # Commit ultimo mese
git shortlog -s -n                               # Contributi per autore
```

### Ricerca nelle Modifiche
```bash
git log --grep="Priority" --oneline              # Commit con "Priority"
git log --since="2024-01-01" -- issues/         # Modifiche da gennaio
```

## Configurazione e Setup

### Requisiti
- **Git installato** sul sistema
- **Permessi di scrittura** nella directory del progetto
- **Python 3.7+** per subprocess calls

### Inizializzazione Automatica
Il sistema si inizializza automaticamente:
1. Crea directory `.jira_tracking`
2. Inizializza repository Git
3. Configura utente Git per commit automatici
4. Crea README e .gitignore iniziali

### Configurazione Git
```bash
git config user.name "Jira Tracker Bot"
git config user.email "jira-tracker@localhost"  
```

## Troubleshooting

### Git Non Trovato
**Errore**: `git: command not found`
**Soluzione**: Installare Git e aggiungerlo al PATH

### Permessi Insufficienti  
**Errore**: `Permission denied creating .jira_tracking`
**Soluzione**: Verificare permessi directory del progetto

### Repository Corrotto
**Errore**: Git repository errors  
**Soluzione**: Eliminare `.jira_tracking` e riavviare l'app

## Migrazione dal Sistema Precedente

### Dati Esistenti
- Le note esistenti nel database **vengono mantenute**
- Il nuovo sistema **non sovrascrive** i dati esistenti  
- **Coesistenza** tra vecchie note e nuovo tracking Git

### Transizione Graduale
- Issues aperti iniziano immediatamente il tracking Git
- Cronologia passata rimane nelle note database
- Nuovo sistema attivo per tutte le modifiche future

## Estensioni Future

### Possibili Miglioramenti
1. **Branch per Progetti**: Branch Git separati per progetti diversi
2. **Sync Distribuito**: Sincronizzazione tra team via Git remoto  
3. **Analytics**: Dashboard con statistiche dalle Git history
4. **API Integration**: Webhook per modifiche esterne
5. **Rollback UI**: Interfaccia per ripristinare versioni precedenti

### Integrazione CI/CD
- **Git Hooks**: Trigger su modifiche specifiche
- **Automated Reports**: Report periodici delle modifiche
- **Backup Automation**: Backup automatici del repository tracking

---

## Conclusione

Il nuovo sistema Git-based rappresenta un significativo upgrade in termini di:
- **Robustezza** del tracking
- **Queryability** dei dati storici  
- **Efficienza** dello storage
- **Flessibilità** per future estensioni

La transizione è **trasparente** per l'utente finale, mantenendo tutte le funzionalità esistenti mentre aggiunge potenti capacità di cronologia e analisi.