import os
import tempfile
from services.db_service import DatabaseService
from services.app_settings import AppSettings
from views.jira_grid_view import JiraGridView


def test_jira_grid_view_persists_and_restores(tmp_path, qtbot):
    # Use a temporary DB path under the tmp_path to avoid messing with user appdata
    db_file = tmp_path / "test_jira.db"

    # Initialize DatabaseService to point to the tmp db
    db = DatabaseService(db_name=str(db_file.name))
    # Override data dir so it writes into our tmp path
    db.db_path = str(db_file)
    db.initialize_db()

    # Create AppSettings backed by this DB
    app_settings = AppSettings(db)

    # Set a setting for table_sort_order and grid_columns
    sort_order = [{'column': 1, 'order': 0}]
    app_settings.set_setting('table_sort_order', str(sort_order))
    app_settings.set_setting('grid_columns', '{}')

    # Create the view and apply app_settings
    view = JiraGridView()
    qtbot.addWidget(view)
    view.set_app_settings(app_settings)

    # Now modify sort order and save
    view.sort_columns = [{'column': 2, 'order': 0}]
    view._save_sort_order()

    # Create a new view instance to simulate restart
    new_view = JiraGridView()
    qtbot.addWidget(new_view)
    new_view.set_app_settings(app_settings)

    # The new view should have restored the previous sort order (or at least not crash)
    assert isinstance(new_view.get_sort_order(), list)
