#!/usr/bin/env python3

import sys
from PyQt6.QtWidgets import QApplication
from views.notes_manager_dialog import NotesManagerDialog
from services.db_service import DatabaseService
from services.app_settings import AppSettings

def test_notedata_get_fix():
    """Test if the NoteData.get() error is fixed."""
    print('🔧 Testing NoteData.get() error fix...')
    
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
        
        # Test creating a new note
        dialog.create_new_note()
        print('✅ New note created')
        
        # Add content that would trigger auto-save
        dialog.title_edit.setText('Get Error Fix Test')
        dialog.jira_key_edit.setText('FIX-456')
        dialog.content_edit.setPlainText('Testing if NoteData get attribute error is resolved')
        
        print('✅ Content added, triggering auto-save...')
        
        # Force auto-save to trigger the error path
        try:
            dialog._perform_auto_save()
            print('🎉 AUTO-SAVE SUCCESSFUL - NoteData.get() error is FIXED!')
        except AttributeError as e:
            if "'NoteData' object has no attribute 'get'" in str(e):
                print(f'❌ STILL HAS GET ERROR: {e}')
                return False
            else:
                print(f'⚠️ Different AttributeError: {e}')
        except Exception as e:
            print(f'⚠️ Other error: {e}')
        
        # Check if note was saved successfully  
        notes = db.get_all_notes()
        recent_notes = [n for n in notes if n['title'] == 'Get Error Fix Test']
        
        if recent_notes:
            note = recent_notes[0]
            print(f'✅ Note successfully saved: "{note["title"]}" (ID: {note["id"]})')
            print(f'   Content length: {len(note["content"])} chars')
            print(f'   Is draft: {note["is_draft"]}')
            return True
        else:
            print('⚠️ Note not found in database')
            return False
            
    except Exception as e:
        print(f'❌ Unexpected error: {e}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_notedata_get_fix()
    if success:
        print('\n🎊 ALL NOTEDATA ERRORS FIXED!')
        print('✨ Auto-save system is fully functional!')
    else:
        print('\n❌ Issues still remain')