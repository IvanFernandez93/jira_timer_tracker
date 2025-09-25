#!/usr/bin/env python3
"""Debug commit button visibility issue."""

import sys
from PyQt6.QtWidgets import QApplication
from views.notes_manager_dialog import NotesManagerDialog
from services.db_service import DatabaseService
from services.app_settings import AppSettings

def main():
    print("🔧 Debugging commit button visibility...")
    
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
        
        # Check initial state
        print(f"🔘 Initial commit button state:")
        print(f"   - Visible: {dialog.commit_btn.isVisible()}")
        print(f"   - Enabled: {dialog.commit_btn.isEnabled()}")
        print(f"   - Text: '{dialog.commit_btn.text()}'")
        print(f"   - Widget exists: {dialog.commit_btn is not None}")
        
        # Force visibility
        print("\n🔧 Forcing visibility...")
        dialog.commit_btn.setVisible(True)
        dialog.commit_btn.setEnabled(True)
        print(f"   - After setVisible(True): {dialog.commit_btn.isVisible()}")
        print(f"   - After setEnabled(True): {dialog.commit_btn.isEnabled()}")
        
        # Test the method directly
        print(f"\n📝 Testing specific lines from _set_note_editing_mode...")
        dialog.commit_btn.setVisible(True)
        dialog.commit_btn.setText("✅ Commit")
        dialog.commit_btn.setToolTip("Committa la nota (readonly)")
        
        print(f"   - After manual setup: visible={dialog.commit_btn.isVisible()}, text='{dialog.commit_btn.text()}'")
        
        # Check if parent widget is visible
        if hasattr(dialog.commit_btn, 'parent'):
            parent = dialog.commit_btn.parent()
            print(f"   - Parent widget visible: {parent.isVisible() if parent else 'No parent'}")
        
        print("\n✨ Debug completed!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()