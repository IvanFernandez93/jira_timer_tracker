#!/usr/bin/env python3

import sys
from PyQt6.QtWidgets import QApplication
from views.notes_manager_dialog import NotesManagerDialog
from services.db_service import DatabaseService
from services.app_settings import AppSettings
import time

def test_button_states():
    """Test button states in different note modes."""
    print('🔍 Testing button behavior in notes dialog...')
    
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
        print('✅ Dialog created')
        
        # Test NEW note creation
        print('\n🆕 Testing NEW note state:')
        dialog.create_new_note()
        
        print(f'   Save button visible: {dialog.save_btn.isVisible()}')
        print(f'   Save button text: "{dialog.save_btn.text()}"')
        print(f'   Commit button visible: {dialog.commit_btn.isVisible()}')
        print(f'   Commit button enabled: {dialog.commit_btn.isEnabled()}')
        print(f'   Commit button text: "{dialog.commit_btn.text()}"')
        
        # Add some content to trigger auto-save
        print('\n📝 Adding content to trigger auto-save...')
        dialog.title_edit.setText('Test Note')
        dialog.jira_key_edit.setText('TEST-123')
        dialog.content_edit.setPlainText('This is test content to trigger auto-save')
        
        # Manually trigger auto-save check
        print('   Triggering auto-save manually...')
        dialog._perform_auto_save()
        
        print('\n📋 After auto-save trigger:')
        print(f'   Save button visible: {dialog.save_btn.isVisible()}')  
        print(f'   Commit button enabled: {dialog.commit_btn.isEnabled()}')
        if dialog.current_note_state:
            print(f'   Current state: {dialog.current_note_state.state_name}')
        else:
            print('   Current state: None')
        
        # Get all notes to see if it was saved
        notes = db.get_all_notes()
        print(f'\n📚 Total notes in database: {len(notes)}')
        
        if notes:
            latest_note = notes[0]  # Should be most recent
            print(f'   Latest note: "{latest_note["title"]}" (ID: {latest_note["id"]})')
            print(f'   Is draft: {latest_note["is_draft"]}')
            print(f'   JIRA key: {latest_note["jira_key"]}')
        
        print('\n✨ TEST COMPLETED!')
        
        # Test recommendations
        print('\n💡 DIAGNOSTIC RESULTS:')
        if not dialog.save_btn.isVisible():
            print('✅ CORRECT: Save button is hidden (auto-save active)')
        else:
            print('❌ ISSUE: Save button should be hidden')
            
        if dialog.commit_btn.isEnabled():
            print('✅ CORRECT: Commit button is enabled after content')
        else:
            print('❌ ISSUE: Commit button should be enabled after auto-save')
        
    except Exception as e:
        print(f'❌ Error: {e}')
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_button_states()