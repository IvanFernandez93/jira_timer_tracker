#!/usr/bin/env python3
"""Test file watcher functionality."""

import sys
import time
import tempfile
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from views.notes_manager_dialog import NotesManagerDialog
from services.db_service import DatabaseService
from services.app_settings import AppSettings

def main():
    print("🔧 Testing file watcher functionality...")
    
    try:
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        
        # Initialize services
        db = DatabaseService()
        db.initialize_db()
        app_settings = AppSettings(db)
        
        # Create dialog
        dialog = NotesManagerDialog(db_service=db, app_settings=app_settings)
        dialog.show()
        print("✅ Dialog created and shown")
        
        # Create a test note
        print("🆕 Creating test note...")
        dialog.create_new_note()
        dialog.title_edit.setText("Test File Watcher Note")
        dialog.jira_key_edit.setText("TEST-456")
        dialog.content_edit.setPlainText("Initial content for file watching test")
        
        # Trigger auto-save to create the file
        dialog._perform_auto_save()
        time.sleep(0.5)  # Wait for auto-save
        
        if not dialog.current_note_id:
            print("❌ Failed to create note")
            return
        
        note_id = dialog.current_note_id
        print(f"✅ Note created with ID: {note_id}")
        
        # Get the file path
        file_path = dialog.fs_manager.get_note_file_path("TEST-456", "Test File Watcher Note", note_id)
        print(f"📁 Note file path: {file_path}")
        
        if not file_path.exists():
            print(f"❌ File does not exist: {file_path}")
            return
        
        print(f"✅ File exists: {file_path}")
        
        # Test external modification
        def modify_file_externally():
            try:
                print("✏️ Modifying file externally...")
                new_content = "MODIFIED EXTERNALLY - This content was changed outside the application!"
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                
                print("✅ File modified externally")
                
            except Exception as e:
                print(f"❌ Error modifying file: {e}")
        
        def check_result():
            try:
                current_content = dialog.content_edit.toPlainText()
                print(f"📝 Current content in editor: '{current_content[:50]}...'")
                
                # Close and clean up
                dialog.close()
                app.quit()
                print("🎉 File watcher test completed!")
                
            except Exception as e:
                print(f"❌ Error checking result: {e}")
        
        # Schedule external modification after 2 seconds
        QTimer.singleShot(2000, modify_file_externally)
        
        # Check result after 5 seconds
        QTimer.singleShot(5000, check_result)
        
        print("⏳ Test in progress... External modification will happen in 2 seconds")
        
        # Run the application
        app.exec()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()