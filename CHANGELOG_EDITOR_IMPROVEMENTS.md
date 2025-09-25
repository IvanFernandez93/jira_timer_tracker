# Markdown Editor Improvements - Changelog

## Modifiche Implementate

### 1. Editor Markdown a 3 Modalità

**Modifiche in `views/markdown_editor.py`:**

- **Nuova Struttura delle Modalità:**
  - `view_mode = 0`: Solo editore (Edit Only)
  - `view_mode = 1`: Solo anteprima (Preview Only) 
  - `view_mode = 2`: Side-by-side (Edit + Preview)

- **Nuovo Layout:**
  - `editor`: Editor principale per modalità edit-only
  - `preview_browser`: Browser di anteprima per modalità preview-only
  - `combined_widget`: Widget combinato per modalità side-by-side
    - `editor_combined`: Editor per modalità side-by-side
    - `preview_combined`: Anteprima per modalità side-by-side

- **Sincronizzazione Automatica:**
  - Sincronizzazione bidirezionale tra `editor` e `editor_combined`
  - Prevenzione dei loop infiniti con disconnect/connect temporanei
  - Aggiornamento automatico dell'anteprima durante la modifica

- **Funzioni Aggiornate:**
  - `toggle_preview()`: Cicla tra le 3 modalità
  - `get_active_editor()`: Restituisce l'editor attualmente attivo
  - Tutti i metodi di formattazione ora utilizzano l'editor corretto
  - Metodi pubblici (`setMarkdown`, `toMarkdown`, etc.) sincronizzano entrambi gli editor

### 2. Sistema di Tracking delle Variazioni

**Modifiche in `controllers/jira_detail_controller.py`:**

- **Rimossa Gestione Automatica Note:**
  - Eliminata chiamata automatica a `_create_or_update_auto_note()`
  - Le note automatiche non vengono più create all'apertura degli issue

- **Nuovo Sistema di Tracking:**
  - `_track_issue_changes()`: Rileva variazioni nei ticket Jira
  - Confronto basato su hash MD5 dei dati sensibili
  - Campi monitorati: summary, status, priority, assignee, description
  - Creazione automatica di note di log per le variazioni rilevate

**Modifiche in `services/db_service.py`:**

- **Nuova Tabella:**
  ```sql
  CREATE TABLE IF NOT EXISTS IssueTrackingState (
      JiraKey TEXT PRIMARY KEY,
      ContentHash TEXT NOT NULL,
      TrackingData TEXT NOT NULL,
      LastUpdated DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
  );
  ```

- **Nuovi Metodi:**
  - `get_issue_tracking_state(jira_key)`: Recupera l'ultimo stato noto
  - `set_issue_tracking_state(jira_key, hash, data)`: Aggiorna lo stato di tracking

### 3. Comportamento del Sistema

**Prima delle Modifiche:**
- Editor a 2 modalità (edit-only ↔ side-by-side)
- Creazione automatica di note "Auto: Issue Details"
- Possibili note duplicate per lo stesso contenuto

**Dopo le Modifiche:**
- Editor a 3 modalità (edit-only → preview-only → side-by-side → edit-only)
- Nessuna creazione automatica di note
- Sistema di tracking che registra solo le variazioni effettive
- Note di log create automaticamente quando i campi importanti cambiano

### 4. Funzionalità del Tracking

- **Rilevamento Automatico:** Il sistema confronta automaticamente lo stato attuale con l'ultimo stato salvato
- **Log Dettagliato:** Crea note specifiche che mostrano cosa è cambiato (da → a)
- **Prevenzione Spam:** Non crea log se non ci sono variazioni reali
- **Tagging Automatico:** Le note di tracking sono taggate con "auto-tracking,change-log"

### 5. Esempio di Note di Tracking

```markdown
## Changes detected on 15 Jan 2024 at 14:30

- **Status**: `In Progress` → `Done`
- **Assignee**: `John Smith` → `Jane Doe`
- **Priority**: `High` → `Medium`
```

## Benefici delle Modifiche

1. **Maggiore Flessibilità:** Tre modalità di visualizzazione per diverse preferenze di lavoro
2. **Riduzione del Rumore:** Eliminazione delle note automatiche duplicate
3. **Tracking Intelligente:** Registrazione solo delle variazioni significative
4. **Migliore UX:** Sincronizzazione fluida tra le modalità dell'editor
5. **Controllo Utente:** L'utente ha pieno controllo sulla creazione delle note

## Compatibilità

- Tutte le funzioni pubbliche dell'editor mantengono la stessa interfaccia
- Le note esistenti non vengono modificate
- Il database viene aggiornato automaticamente con la nuova tabella
- Retrocompatibilità completa con il codice esistente