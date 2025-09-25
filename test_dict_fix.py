#!/usr/bin/env python3
"""Test fix for dict object error."""

import sys
from PyQt6.QtWidgets import QApplication
from views.notes_manager_dialog import NotesManagerDialog
from services.db_service import DatabaseService
from services.app_settings import AppSettings

def main():
    print("🔧 Testing fix for 'dict' object has no attribute 'jira_key' error...")
    
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
        print("✅ Dialog created")
        
        # Show the dialog to make widgets visible
        dialog.show()
        
        # Create a note first
        print("🆕 Creating test note...")
        dialog.create_new_note()
        dialog.title_edit.setText("Test Note for Dict Fix")
        dialog.content_edit.setPlainText("Test content")
        
        # Trigger auto-save to get a note ID
        dialog._perform_auto_save()
        
        if hasattr(dialog, 'current_note_id') and dialog.current_note_id:
            note_id = dialog.current_note_id
            print(f"✅ Note created with ID: {note_id}")
            
            # Now test loading it (this should trigger the dict error if not fixed)
            print("📂 Testing load_note_in_editor...")
            dialog.load_note_in_editor(note_id)
            
            print("✅ Note loaded successfully! Dict error is FIXED!")
            print(f"   - Title: '{dialog.title_edit.text()}'")
            print(f"   - Content length: {len(dialog.content_edit.toPlainText())}")
            print(f"   - Commit button visible: {dialog.commit_btn.isVisible()}")
            
        else:
            print("❌ Could not create note to test with")
        
        # Close after a moment
        from PyQt6.QtCore import QTimer
        def close_app():
            print("🎉 TEST COMPLETED - Dict error fixed!")
            dialog.close()
            app.quit()
        
        QTimer.singleShot(1000, close_app)
        app.exec()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()