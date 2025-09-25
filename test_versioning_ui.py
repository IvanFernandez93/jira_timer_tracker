#!/usr/bin/env python3
"""
Test rapido per il sistema di cronologia versioni delle note
"""
import sys
import os

# Aggiungi la directory root al path per gli import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton
from PyQt6.QtCore import Qt

from services.db_service import DatabaseService
from services.git_service import GitService  
from services.note_manager import NoteManager
from views.note_version_history_dialog import NoteVersionHistoryDialog

class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Test Cronologia Versioni Note")
        self.setGeometry(100, 100, 400, 200)
        
        # Inizializza servizi
        self.db_service = DatabaseService()
        self.git_service = GitService()
        self.note_manager = NoteManager(self.db_service, self.git_service)
        
        # Crea widget centrale
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Pulsante per creare una nota di test
        self.create_note_btn = QPushButton("📝 Crea Nota di Test")
        self.create_note_btn.clicked.connect(self.create_test_note)
        layout.addWidget(self.create_note_btn)
        
        # Pulsante per aprire cronologia
        self.history_btn = QPushButton("📜 Apri Cronologia")
        self.history_btn.clicked.connect(self.open_history)
        self.history_btn.setEnabled(False)
        layout.addWidget(self.history_btn)
        
        self.test_note_id = None
        
    def create_test_note(self):
        """Crea una nota di test con diverse versioni."""
        try:
            # Crea nota iniziale
            note_data = {
                'title': 'Test Cronologia Versioni',
                'jira_key': 'TEST-123',
                'content': '# Nota di Test\n\nQuesta è la versione iniziale della nota.',
                'tags': 'test,versioning',
                'is_fictitious': False
            }
            
            success, note_id = self.note_manager.create_new_note(note_data)
            if not success:
                print("❌ Errore nella creazione della nota")
                return
                
            self.test_note_id = note_id
            print(f"✅ Nota creata con ID: {note_id}")
            
            # Simula alcune modifiche per creare versioni
            # Versione 2: aggiunta contenuto
            self.note_manager.save_draft(note_id, {
                'content': '# Nota di Test\n\nQuesta è la versione iniziale.\n\n## Aggiunta\n\nQuesta è una seconda versione con contenuto aggiunto.'
            })
            print("✅ Salvata bozza versione 2")
            
            # Commit della seconda versione
            self.note_manager.commit_note(note_id, 'Aggiunto contenuto extra')
            print("✅ Commit versione 2")
            
            # Versione 3: modifica maggiore
            self.note_manager.save_draft(note_id, {
                'content': '''# Nota di Test Avanzata

Questa è una versione completamente riscritta della nota.

## Sezioni
1. Introduzione
2. Dettagli
3. Conclusioni

### Introduzione
Lorem ipsum dolor sit amet...

### Dettagli  
Contenuto dettagliato qui.

### Conclusioni
Riepilogo finale.
'''
            })
            print("✅ Salvata bozza versione 3")
            
            # Commit della terza versione
            self.note_manager.commit_note(note_id, 'Riscrittura completa della nota')
            print("✅ Commit versione 3")
            
            # Abilita pulsante cronologia
            self.history_btn.setEnabled(True)
            print("🎉 Note di test create! Ora puoi aprire la cronologia.")
            
        except Exception as e:
            print(f"❌ Errore: {e}")
            import traceback
            traceback.print_exc()
            
    def open_history(self):
        """Apre il dialog cronologia versioni."""
        if not self.test_note_id:
            return
            
        try:
            dialog = NoteVersionHistoryDialog(
                note_manager=self.note_manager,
                note_id=self.test_note_id,
                note_title="Test Cronologia Versioni",
                parent=self
            )
            dialog.exec()
            
        except Exception as e:
            print(f"❌ Errore apertura cronologia: {e}")
            import traceback
            traceback.print_exc()

def main():
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()