# 📝 Sistema Note Basato su File System

## 🎯 Obiettivo della Refactorizzazione

Trasformare il sistema di note da database-based a file-based per permettere:
- **Editing Esterno**: Utilizzo di editor esterni (VS Code, Obsidian, etc.)
- **Version Control**: Git native per tracking modifiche
- **Portabilità**: Note accessibili senza applicazione
- **Interoperabilità**: Standard markdown per massima compatibilità

## 📁 Struttura Directory Proposta

```
notes/
├── JIRA-123/
│   ├── analisi-tecnica.md
│   ├── meeting-notes.md
│   ├── bug-investigation.md
│   └── .metadata.json
├── PROJ-456/
│   ├── requirements-analysis.md
│   ├── implementation-plan.md
│   └── .metadata.json
├── GENERAL/
│   ├── daily-notes.md
│   ├── ideas-backlog.md
│   └── .metadata.json
└── .notes-config.json
```

## 📋 Formato File Note

### Note Markdown Standard
```markdown
---
title: "Analisi Tecnica Bug Authentication"
jira_key: "JIRA-123"
tags: ["bug", "authentication", "security"]
created_at: "2025-01-15T10:30:00Z"
updated_at: "2025-01-15T14:45:00Z"
is_fictitious: false
---

# Analisi Bug Authentication

## Problema Identificato
- L'utente non riesce ad accedere dopo cambio password
- Stack trace mostra errore 401 Unauthorized

## Investigazione
1. Verificato database utenti ✓
2. Controllato cache sessioni ✓  
3. Analizzato logs applicazione ✓

## Soluzione Proposta
```python
def refresh_user_session():
    # Clear cached credentials
    cache.invalidate_user_tokens()
    # Force re-authentication
    return authenticate_user()
```

## Next Steps
- [ ] Implementare fix
- [ ] Test su ambiente staging  
- [ ] Deploy in produzione
```

### Metadata File (.metadata.json)
```json
{
  "jira_key": "JIRA-123",
  "notes": [
    {
      "filename": "analisi-tecnica.md",
      "title": "Analisi Tecnica Bug Authentication", 
      "created_at": "2025-01-15T10:30:00Z",
      "updated_at": "2025-01-15T14:45:00Z",
      "tags": ["bug", "authentication", "security"],
      "word_count": 245,
      "checksum": "sha256:a1b2c3d4..."
    },
    {
      "filename": "meeting-notes.md",
      "title": "Meeting Notes - Bug Triage",
      "created_at": "2025-01-14T09:00:00Z", 
      "updated_at": "2025-01-14T10:30:00Z",
      "tags": ["meeting", "triage"],
      "word_count": 156,
      "checksum": "sha256:e5f6g7h8..."
    }
  ],
  "last_sync": "2025-01-15T14:45:00Z"
}
```

### Config Globale (.notes-config.json)
```json
{
  "version": "1.0",
  "settings": {
    "default_editor": "code",
    "auto_git_commit": true,
    "git_commit_message_template": "📝 Updated notes for {jira_key}: {title}",
    "file_naming_pattern": "{title_slug}.md",
    "tags_autocomplete": true,
    "sync_external_changes": true
  },
  "templates": {
    "bug_analysis": "templates/bug-template.md",
    "meeting_notes": "templates/meeting-template.md", 
    "task_planning": "templates/task-template.md"
  },
  "integrations": {
    "git": {
      "enabled": true,
      "auto_commit": true,
      "commit_on_save": false,
      "commit_on_close": true
    },
    "external_editors": {
      "vscode": "code",
      "obsidian": "obsidian://open?path=",
      "typora": "typora"
    }
  }
}
```

## 🔄 Piano di Migrazione

### Phase 1: Servizio File System
```python
class FileSystemNotesService:
    """Servizio per gestione note su file system."""
    
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.git_service = GitService(base_path)
        self._ensure_structure()
    
    def create_note(self, jira_key: str, title: str, content: str, 
                   tags: list = None) -> Path:
        """Crea una nuova nota su file system."""
        pass
    
    def update_note(self, note_path: Path, content: str, 
                   frontmatter: dict = None) -> bool:
        """Aggiorna nota esistente."""
        pass
    
    def get_note(self, jira_key: str, title: str) -> dict:
        """Legge nota da file system."""
        pass
    
    def list_notes(self, jira_key: str = None) -> list:
        """Lista tutte le note, opzionalmente per jira_key."""
        pass
    
    def delete_note(self, note_path: Path) -> bool:
        """Elimina nota (soft delete con Git)."""
        pass
    
    def sync_external_changes(self) -> list:
        """Rileva modifiche esterne e sincronizza metadata."""
        pass
```

### Phase 2: Migrazione Dati Esistenti  
```python
class DatabaseToFileSystemMigrator:
    """Migra note esistenti da DB a file system."""
    
    def migrate_all_notes(self, db_service: DatabaseService, 
                         fs_service: FileSystemNotesService):
        """Migrazione completa con backup."""
        
        # 1. Backup database esistente
        backup_path = self._create_backup()
        
        # 2. Estrai tutte le note
        notes = db_service.get_all_annotations()
        
        # 3. Converti in file markdown
        for note in notes:
            self._convert_note_to_file(note, fs_service)
        
        # 4. Verifica integrità
        self._verify_migration(db_service, fs_service)
        
        # 5. Git commit iniziale  
        fs_service.git_service.commit_all("📦 Initial migration from database")
```

### Phase 3: UI Integration
```python
class NotesFileSystemController:
    """Controller per gestione note file-based."""
    
    def __init__(self, fs_service: FileSystemNotesService):
        self.fs_service = fs_service
        self.file_watcher = QFileSystemWatcher()
        self.file_watcher.fileChanged.connect(self._on_external_change)
    
    def open_in_external_editor(self, note_path: Path, editor: str = None):
        """Apre nota nell'editor esterno configurato."""
        pass
    
    def watch_external_changes(self, note_path: Path):
        """Monitora modifiche esterne al file."""
        pass
    
    def _on_external_change(self, file_path: str):
        """Gestisce modifiche esterne rilevate."""
        pass
```

## 🛠️ Implementazione Dettagliata

### 1. Gestione Filename
```python
def generate_filename(title: str) -> str:
    """Genera filename sicuro da titolo."""
    # Rimuovi caratteri non validi
    safe_title = re.sub(r'[<>:"/\\|?*]', '', title)
    # Converti a slug  
    slug = safe_title.lower().replace(' ', '-')
    # Limita lunghezza
    return slug[:50] + '.md'

def ensure_unique_filename(directory: Path, filename: str) -> str:
    """Assicura filename univoco aggiungendo numero se necessario."""
    base, ext = filename.rsplit('.', 1)
    counter = 1
    while (directory / filename).exists():
        filename = f"{base}-{counter}.{ext}"
        counter += 1
    return filename
```

### 2. Frontmatter Parser
```python
import frontmatter

def parse_note_file(file_path: Path) -> tuple[dict, str]:
    """Estrae frontmatter e contenuto da file markdown."""
    with open(file_path, 'r', encoding='utf-8') as f:
        post = frontmatter.load(f)
    
    metadata = post.metadata
    content = post.content
    
    return metadata, content

def write_note_file(file_path: Path, metadata: dict, content: str):
    """Scrive nota con frontmatter su file."""
    post = frontmatter.Post(content, **metadata)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(frontmatter.dumps(post))
```

### 3. External Editor Integration
```python
def open_with_external_editor(file_path: Path, editor: str = "code"):
    """Apre file con editor esterno."""
    editors = {
        "code": ["code", str(file_path)],
        "notepad++": ["notepad++", str(file_path)], 
        "typora": ["typora", str(file_path)],
        "obsidian": ["obsidian", f"obsidian://open?path={file_path}"]
    }
    
    if editor in editors:
        subprocess.Popen(editors[editor])
    else:
        # Fallback a editor di sistema
        os.startfile(file_path)  # Windows
        # subprocess.call(["open", file_path])  # macOS  
        # subprocess.call(["xdg-open", file_path])  # Linux
```

### 4. File Watching per External Changes
```python
class NotesFileWatcher(QObject):
    """Monitora modifiche esterne ai file di note."""
    
    file_changed = pyqtSignal(str)  # file_path
    
    def __init__(self):
        super().__init__()
        self.watcher = QFileSystemWatcher()
        self.watcher.fileChanged.connect(self._on_file_changed)
        self.watched_files = {}
    
    def watch_file(self, file_path: Path):
        """Inizia monitoraggio file."""
        str_path = str(file_path)
        if str_path not in self.watched_files:
            self.watcher.addPath(str_path)
            self.watched_files[str_path] = file_path.stat().st_mtime
    
    def _on_file_changed(self, file_path: str):
        """Gestisce modifica rilevata."""
        try:
            current_mtime = Path(file_path).stat().st_mtime
            if current_mtime != self.watched_files.get(file_path):
                self.watched_files[file_path] = current_mtime
                self.file_changed.emit(file_path)
        except FileNotFoundError:
            # File eliminato
            self.watcher.removePath(file_path)
            del self.watched_files[file_path]
```

## 🔧 Dropdown JQL Fix

### Problema Identificato
```python
# in views/jira_grid_view.py - Problema populate_jql_favorites
def populate_jql_favorites(self, favorites):
    """Popola dropdown JQL con preferiti."""
    # PROBLEMA: Metodo non esiste o non funziona correttamente
    pass
```

### Soluzione Implementata
```python
def populate_jql_favorites(self, favorites):
    """Popola la combo JQL con query preferite."""
    # Salva selezione corrente
    current_text = self.jql_combo.currentText()
    
    # Blocca segnali temporaneamente
    self.jql_combo.blockSignals(True)
    
    try:
        # Pulisci combo
        self.jql_combo.clear()
        
        # Aggiungi query preferite
        for fav in favorites:
            self.jql_combo.addItem(fav['display_name'], fav['jql'])
        
        # Ripristina testo se era presente
        if current_text:
            index = self.jql_combo.findText(current_text)
            if index >= 0:
                self.jql_combo.setCurrentIndex(index)
            else:
                self.jql_combo.setCurrentText(current_text)
                
    finally:
        # Riabilita segnali
        self.jql_combo.blockSignals(False)

def get_jql_text(self) -> str:
    """Ottiene il testo JQL corrente."""
    return self.jql_combo.currentText()

def set_jql_text(self, jql: str):
    """Imposta il testo JQL."""
    self.jql_combo.setCurrentText(jql)
```

## 🚀 Benefici del Nuovo Sistema

### Per Utenti
- **Editing Flessibile**: Usa il tuo editor preferito
- **Portabilità**: Note accessibili ovunque  
- **Version Control**: Storia completa modifiche
- **Backup Naturale**: Git repos facilmente backuppabili

### Per Sviluppatori
- **Separation of Concerns**: Logic separata da storage
- **Testing**: File system facilmente mockabile
- **Performance**: No database overhead per letture
- **Standards**: Markdown universalmente supportato

### Per Sistema
- **Scalabilità**: File system nativo del SO
- **Robustezza**: No database corruption risks
- **Interoperabilità**: Standard aperti
- **Estendibilità**: Plugin system più semplice

---

## 📅 Timeline Implementazione

### Week 1: Foundation
- [ ] `FileSystemNotesService` base implementation
- [ ] Frontmatter parsing utilities  
- [ ] Basic file operations (CRUD)

### Week 2: Migration
- [ ] `DatabaseToFileSystemMigrator` 
- [ ] Data validation and integrity checks
- [ ] Backup and rollback mechanisms

### Week 3: Integration  
- [ ] Update UI controllers
- [ ] File watching implementation
- [ ] External editor integration

### Week 4: Polish
- [ ] Error handling refinement
- [ ] Performance optimization
- [ ] Documentation and testing

### Week 5: Dropdown JQL Fix
- [ ] Debug existing `populate_jql_favorites` 
- [ ] Implement proper combo box handling
- [ ] Test with various JQL scenarios

---

## 🎯 Success Metrics

- ✅ **Migration Success**: 100% note data preserved
- ✅ **Editor Integration**: 3+ external editors supported
- ✅ **Performance**: <100ms file operations
- ✅ **Reliability**: Git history intact
- ✅ **UX**: Seamless transition for users
- ✅ **JQL Dropdown**: Functional favorite selection