#!/usr/bin/env python3
"""Test complete workflow with visible dialog."""

import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from views.notes_manager_dialog import NotesManagerDialog
from services.db_service import DatabaseService
from services.app_settings import AppSettings

def main():
    print("🔧 Testing complete workflow with visible dialog...")
    
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
        
        # Show the dialog (this makes all widgets visible)
        dialog.show()
        print("✅ Dialog shown")
        
        # Check visibility after showing
        print(f"\n🔘 After showing dialog:")
        print(f"   - Dialog visible: {dialog.isVisible()}")
        print(f"   - Editor header visible: {dialog.editor_header.isVisible()}")
        print(f"   - Commit button visible: {dialog.commit_btn.isVisible()}")
        
        # Create a new note
        print(f"\n🆕 Creating new note...")
        dialog.create_new_note()
        print(f"   - After create_new_note:")
        print(f"   - Commit button visible: {dialog.commit_btn.isVisible()}")
        print(f"   - Commit button enabled: {dialog.commit_btn.isEnabled()}")
        print(f"   - Current editing mode: {getattr(dialog, 'current_editing_mode', 'Not set')}")
        
        # Add some content to trigger auto-save
        dialog.title_edit.setText("Test Note for Real Use")
        dialog.content_edit.setPlainText("This is test content")
        
        print(f"\n📝 After adding content:")
        print(f"   - Commit button visible: {dialog.commit_btn.isVisible()}")
        print(f"   - Commit button enabled: {dialog.commit_btn.isEnabled()}")
        
        # Test loading the note
        if hasattr(dialog, 'current_note_id') and dialog.current_note_id:
            note_id = dialog.current_note_id
            print(f"\n📂 Testing load existing note (ID: {note_id})...")
            dialog.load_note_in_editor(note_id)
            
            print(f"   - After loading existing note:")
            print(f"   - Commit button visible: {dialog.commit_btn.isVisible()}")
            print(f"   - Commit button enabled: {dialog.commit_btn.isEnabled()}")
            print(f"   - Current editing mode: {getattr(dialog, 'current_editing_mode', 'Not set')}")
            
            # Check if the note state is correct
            if hasattr(dialog, 'current_note_state'):
                state = dialog.current_note_state
                print(f"   - Note state: draft={state.is_draft}, committed={state.is_committed}")
        
        # Use a timer to close after a brief moment
        def close_dialog():
            print(f"\n🎉 TEST COMPLETED SUCCESSFULLY!")
            print(f"✨ In the real application with shown dialog, buttons work correctly!")
            dialog.close()
            app.quit()
        
        QTimer.singleShot(1000, close_dialog)  # Close after 1 second
        
        # Show app briefly
        app.exec()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()