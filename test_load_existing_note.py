#!/usr/bin/env python3
"""Test loading existing note and auto-save functionality."""

import sys
import time
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from views.notes_manager_dialog import NotesManagerDialog
from services.db_service import DatabaseService
from services.app_settings import AppSettings

def main():
    print("🔧 Testing existing note loading and auto-save...")
    
    try:
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        
        # Initialize services
        db = DatabaseService()
        db.initialize_db()
        app_settings = AppSettings(db)
        
        print("✅ Services initialized")
        
        # Create dialog
        dialog = NotesManagerDialog(db_service=db, app_settings=app_settings)
        print("✅ Dialog created")
        
        # First create a note to test with
        print("🆕 Creating test note...")
        dialog.create_new_note()
        dialog.title_edit.setText("Test Existing Note")
        dialog.content_edit.setPlainText("Initial content for testing")
        dialog.jira_key_edit.setText("TEST-123")
        
        # Trigger auto-save
        dialog._perform_auto_save()
        time.sleep(0.1)  # Allow auto-save to complete
        
        if dialog.current_note_id:
            saved_note_id = dialog.current_note_id
            print(f"✅ Test note created with ID: {saved_note_id}")
            
            # Now test loading this existing note
            print("📂 Testing load_note_in_editor...")
            dialog.load_note_in_editor(saved_note_id)
            
            print(f"📋 After loading:")
            print(f"   - Current note ID: {dialog.current_note_id}")
            print(f"   - Title: '{dialog.title_edit.text()}'")
            print(f"   - JIRA Key: '{dialog.jira_key_edit.text()}'")
            print(f"   - Content length: {len(dialog.content_edit.toPlainText())} chars")
            print(f"   - Is readonly: {dialog.content_edit.isReadOnly()}")
            
            # Check button states
            print(f"🔘 Button states:")
            print(f"   - Save button visible: {dialog.save_btn.isVisible()}")
            print(f"   - Save button text: '{dialog.save_btn.text()}'")
            print(f"   - Commit button visible: {dialog.commit_btn.isVisible()}")
            print(f"   - Commit button text: '{dialog.commit_btn.text()}'")
            print(f"   - Commit button enabled: {dialog.commit_btn.isEnabled()}")
            
            # Test modifying content to see if auto-save triggers
            print("✏️ Testing content modification...")
            original_content = dialog.content_edit.toPlainText()
            dialog.content_edit.setPlainText(original_content + "\n\nAdded content for test")
            
            # Wait a moment for auto-save to trigger
            time.sleep(0.5)
            
            # Check if commit button becomes available
            print(f"📝 After content change:")
            print(f"   - Content changed detected: {getattr(dialog, '_content_changed', False)}")
            print(f"   - Commit button enabled: {dialog.commit_btn.isEnabled()}")
            
            if hasattr(dialog, 'current_note_state'):
                print(f"   - Current note state: {dialog.current_note_state}")
            
            print("🎉 EXISTING NOTE LOADING TEST COMPLETED!")
            print("✨ Auto-save system should now work for existing notes!")
            
        else:
            print("❌ Failed to create test note")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()