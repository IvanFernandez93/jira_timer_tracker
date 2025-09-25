#!/usr/bin/env python3
"""Debug widget hierarchy visibility."""

import sys
from PyQt6.QtWidgets import QApplication, QWidget
from views.notes_manager_dialog import NotesManagerDialog
from services.db_service import DatabaseService
from services.app_settings import AppSettings

def check_widget_hierarchy(widget, name="", level=0):
    """Recursively check visibility of widget hierarchy."""
    indent = "  " * level
    visible = widget.isVisible()
    print(f"{indent}{name}: visible={visible}, type={type(widget).__name__}")
    
    if hasattr(widget, 'parent') and widget.parent():
        check_widget_hierarchy(widget.parent(), f"{name}_parent", level + 1)

def main():
    print("🔧 Debugging widget hierarchy visibility...")
    
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
        
        # Check hierarchy
        print(f"\n🔍 Widget hierarchy for commit_btn:")
        check_widget_hierarchy(dialog.commit_btn, "commit_btn")
        
        print(f"\n🔍 Direct parent checks:")
        print(f"   - editor_header visible: {dialog.editor_header.isVisible()}")
        print(f"   - right_panel visible: {dialog.right_panel.isVisible()}")
        print(f"   - dialog visible: {dialog.isVisible()}")
        
        # Try to make everything visible
        print(f"\n🔧 Making all parent widgets visible...")
        dialog.editor_header.setVisible(True)
        dialog.right_panel.setVisible(True)
        dialog.setVisible(True)
        
        print(f"   - After making parents visible:")
        print(f"   - editor_header visible: {dialog.editor_header.isVisible()}")
        print(f"   - commit_btn visible: {dialog.commit_btn.isVisible()}")
        
        # Now try the commit button
        dialog.commit_btn.setVisible(True)
        print(f"   - After setVisible(True) on commit_btn: {dialog.commit_btn.isVisible()}")
        
        print("\n✨ Hierarchy debug completed!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()