#!/usr/bin/env python3
"""Simple test for button visibility in draft mode."""

import sys
from PyQt6.QtWidgets import QApplication
from views.notes_manager_dialog import NotesManagerDialog
from services.db_service import DatabaseService
from services.app_settings import AppSettings

def main():
    print("🔧 Testing button visibility in draft mode...")
    
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
        
        # Test setting draft mode directly
        print("📝 Testing _set_note_editing_mode('draft')...")
        dialog._set_note_editing_mode('draft')
        
        print(f"🔘 After setting draft mode:")
        print(f"   - Save button visible: {dialog.save_btn.isVisible()}")
        print(f"   - Commit button visible: {dialog.commit_btn.isVisible()}")
        print(f"   - Commit button enabled: {dialog.commit_btn.isEnabled()}")
        print(f"   - Commit button text: '{dialog.commit_btn.text()}'")
        print(f"   - Content readonly: {dialog.content_edit.isReadOnly()}")
        
        # Test setting committed mode
        print("\n📋 Testing _set_note_editing_mode('committed')...")
        dialog._set_note_editing_mode('committed')
        
        print(f"🔘 After setting committed mode:")
        print(f"   - Save button visible: {dialog.save_btn.isVisible()}")
        print(f"   - Save button text: '{dialog.save_btn.text()}'")
        print(f"   - Commit button visible: {dialog.commit_btn.isVisible()}")
        print(f"   - Commit button text: '{dialog.commit_btn.text()}'")
        print(f"   - Content readonly: {dialog.content_edit.isReadOnly()}")
        
        print("\n✨ Button mode testing completed!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()