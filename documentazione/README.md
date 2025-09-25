# 📚 Documentazione Progetto JIRA Timer Tracker

Questa cartella contiene tutta la documentazione del progetto organizzata per categoria.

## 📁 Struttura Documentazione

### 📋 File Principali
- **00_RIASSUNTO_COMPLETO.md** - Overview completo del progetto e stato implementazioni
- **01_ARCHITETTURA_GENERALE.md** - Architettura sistema e pattern utilizzati
- **02_SERVIZI_CORE.md** - Documentazione dettagliata servizi backend
- **03_PIANO_REFACTORING_NOTE.md** - Piano migrazione sistema note file-based
- **FIX_JQL_DROPDOWN.md** - Documentazione fix bug JQL dropdown

### 📂 Sottocartelle

#### `requisiti/`
Contiene tutti i file di requisiti e dipendenze:
- **requisit_jira_desktop.md** - Requisiti funzionali JIRA desktop
- **requirements.txt** - Dipendenze Python runtime
- **requirements-dev.txt** - Dipendenze Python sviluppo

#### `implementazioni/`
Documentazione dettagliata delle implementazioni e fix:
- **TECHNICAL_DOCS_GIT_TRACKING.md** - Documentazione tecnica Git tracking
- **STARTUP_FIXES_SUMMARY.md** - Riassunto fix problemi startup  
- **RISOLUZIONE_PROBLEMI_GIT.md** - Risoluzione problemi Git
- **RIEPILOGO_COMPLETO_IMPLEMENTAZIONI.md** - Riepilogo implementazioni
- **REFACTOR_NOTES.md** - Documentazione refactoring note
- **PROBLEMA_RISOLTO_DEFINITIVAMENTE.md** - Fix definitivi problemi
- **PROBLEMA_RISOLTO_COMPLETAMENTE.md** - Risoluzione completa problemi
- **GUIDA_UTENTE_GIT_TRACKING.md** - Guida utente Git tracking
- **GIT_TRACKING_DOCUMENTATION.md** - Documentazione Git tracking
- **CHANGELOG_EDITOR_IMPROVEMENTS.md** - Changelog miglioramenti editor
- **ASYNC_LOADING_SOLUTION.md** - Soluzione caricamento asincrono
- **ASYNC_STARTUP_DOCUMENTATION.md** - Documentazione startup asincrono

#### `test_diagnostici/`
Script di test e diagnosi per debugging e verifica:
- **test_jql_*.py** - Test sistema JQL dropdown
- **test_async_*.py** - Test sistema asincrono
- **test_git_system.py** - Test sistema Git
- **test_fictitious_system.py** - Test sistema note fittizie
- **test_ui_integration.py** - Test integrazione UI
- **test_notification_suppression.py** - Test soppressione notifiche
- **test_startup_final.py** - Test finale startup
- **test_refactor_notes.py** - Test refactoring note
- **test_icon_setup.py** - Test setup icone
- **test_logic.py** - Test logica generale
- **populate_default_jqls.py** - Script popolazione JQL default

## 🎯 Come Usare Questa Documentazione

1. **Per Overview Generale**: Inizia con `00_RIASSUNTO_COMPLETO.md`
2. **Per Architettura**: Consulta `01_ARCHITETTURA_GENERALE.md`
3. **Per Servizi Backend**: Vedi `02_SERVIZI_CORE.md`
4. **Per Requisiti**: Controlla cartella `requisiti/`
5. **Per Implementazioni**: Esplora cartella `implementazioni/`
6. **Per Test e Debug**: Usa script in `test_diagnostici/`

## 📝 Mantenimento

- Aggiornare la documentazione ad ogni major change
- Utilizzare i test diagnostici per verificare funzionalità
- Consultare requisiti prima di nuove implementazioni
- Documentare nuovi fix nella cartella implementazioni

---

*Documentazione organizzata: $(Get-Date)*  
*Progetto: JIRA Timer Tracker*  
*Versione: 1.0*