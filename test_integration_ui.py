#!/usr/bin/env python3
"""
Test completo di integrazione UI per il sistema di cronologia versioni
Questo test verifica che tutti i componenti funzionino insieme correttamente.
"""
import sys
import os

# Aggiungi la directory root al path per gli import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel
from PyQt6.QtCore import Qt, QTimer

from services.db_service import DatabaseService
from services.git_service import GitService  
from services.note_manager import NoteManager
from views.markdown_editor import MarkdownEditor

class IntegrationTestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🧪 Test Integrazione Cronologia Versioni")
        self.setGeometry(100, 100, 800, 600)
        
        # Inizializza servizi
        print("🔧 Inizializzazione servizi...")
        self.db_service = DatabaseService()
        self.git_service = GitService()
        self.note_manager = NoteManager(self.db_service, self.git_service)
        
        # Crea widget centrale
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Status label
        self.status_label = QLabel("✅ Sistema inizializzato correttamente")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        
        # Pulsanti test
        self.setup_note_btn = QPushButton("1️⃣ Crea Nota di Test")
        self.setup_note_btn.clicked.connect(self.setup_test_note)
        layout.addWidget(self.setup_note_btn)
        
        self.test_editor_btn = QPushButton("2️⃣ Test Markdown Editor + Cronologia")
        self.test_editor_btn.clicked.connect(self.test_markdown_editor)
        self.test_editor_btn.setEnabled(False)
        layout.addWidget(self.test_editor_btn)
        
        # Markdown Editor per test
        self.editor = MarkdownEditor(show_toolbar=True)
        layout.addWidget(self.editor)
        
        self.test_note_id = None
        
        print("🎯 Finestra test pronta!")
        
    def setup_test_note(self):
        """Crea una nota di test con diverse versioni per testare la cronologia."""
        try:
            self.status_label.setText("📝 Creazione nota di test...")
            
            # Crea nota iniziale
            note_data = {
                'title': 'Test Integrazione UI Cronologia',
                'jira_key': 'UITEST-001',
                'content': '# Test Integrazione UI\n\nQuesta nota testa l\'integrazione completa del sistema cronologia.',
                'tags': 'test,ui,cronologia',
                'is_fictitious': False
            }
            
            success, note_id = self.note_manager.create_new_note(note_data)
            if not success:
                self.status_label.setText("❌ Errore nella creazione della nota")
                return
                
            self.test_note_id = note_id
            
            # Crea diverse versioni
            versions_data = [
                {
                    'content': '''# Test Integrazione UI - Versione 2

Questa nota testa l'integrazione completa del sistema cronologia.

## Funzionalità Testate
- Versionamento automatico
- Cronologia UI
''',
                    'message': 'Aggiunta sezione funzionalità'
                },
                {
                    'content': '''# Test Integrazione UI - Versione 3

Questa nota testa l'integrazione completa del sistema cronologia.

## Funzionalità Testate
- ✅ Versionamento automatico
- ✅ Cronologia UI  
- ✅ Diff viewer esterni
- ✅ Ripristino versioni

## Test Status
Tutti i test stanno passando correttamente!
''',
                    'message': 'Completata documentazione test'
                }
            ]
            
            for i, version_data in enumerate(versions_data, 2):
                # Salva come bozza
                self.note_manager.save_draft(note_id, {
                    'content': version_data['content']
                })
                
                # Commit
                self.note_manager.commit_note(note_id, version_data['message'])
                
                self.status_label.setText(f"✅ Versione {i} creata e committata")
                QApplication.processEvents()  # Aggiorna UI
                
            self.status_label.setText(f"🎉 Nota di test creata! ID: {note_id}\n📜 Ora puoi testare il markdown editor con cronologia")
            self.test_editor_btn.setEnabled(True)
            
        except Exception as e:
            self.status_label.setText(f"❌ Errore: {e}")
            import traceback
            traceback.print_exc()
            
    def test_markdown_editor(self):
        """Testa l'integrazione del markdown editor con il sistema di cronologia."""
        if not self.test_note_id:
            return
            
        try:
            self.status_label.setText("🔧 Configurazione editor con contesto nota...")
            
            # Carica la nota nell'editor
            note = self.db_service.get_note_by_id(self.test_note_id)
            if not note:
                self.status_label.setText("❌ Impossibile caricare la nota")
                return
                
            # Imposta contenuto
            self.editor.setMarkdown(note.get('content', ''))
            
            # Imposta contesto per abilitare cronologia
            note_title = note.get('title', f"Nota {self.test_note_id}")
            self.editor.set_note_context(self.note_manager, self.test_note_id, note_title)
            
            self.status_label.setText(f"""✅ Editor configurato correttamente!
            
📝 Nota caricata: {note_title}
📜 Pulsante cronologia: {"✅ ABILITATO" if hasattr(self.editor, 'history_btn') and self.editor.history_btn.isEnabled() else "❌ NON TROVATO"}
⌨️  Shortcut: Ctrl+H per aprire cronologia
            
🎯 ISTRUZIONI:
1. Clicca il pulsante 📜 nella toolbar dell'editor
2. Oppure usa Ctrl+H
3. Testa ripristino versioni
4. Testa diff esterni con WinMerge

La cronologia dovrebbe mostrare {len(self.note_manager.list_versions(self.test_note_id))} versioni.""")
            
        except Exception as e:
            self.status_label.setText(f"❌ Errore configurazione editor: {e}")
            import traceback
            traceback.print_exc()

def main():
    print("🧪 Avvio Test Integrazione UI Cronologia Versioni")
    print("=" * 60)
    
    app = QApplication(sys.argv)
    
    # Verifica che non ci siano errori di import
    try:
        from views.note_version_history_dialog import NoteVersionHistoryDialog
        from services.external_diff_service import ExternalDiffService
        print("✅ Tutti i moduli importati correttamente")
    except ImportError as e:
        print(f"❌ Errore import moduli: {e}")
        return 1
    
    window = IntegrationTestWindow()
    window.show()
    
    print("🎯 Finestra test aperta! Segui le istruzioni per testare il sistema.")
    return app.exec()

if __name__ == '__main__':
    sys.exit(main())