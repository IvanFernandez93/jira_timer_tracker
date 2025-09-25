import sqlite3
conn = sqlite3.connect('C:/Users/ifernandez/AppData/Roaming/JiraTimeTracker/JiraTimeTracker/jira_tracker.db')
cursor = conn.cursor()
cursor.execute('SELECT name FROM sqlite_master WHERE type=\
table\')
print('Tables:', [table[0] for table in cursor.fetchall()])
cursor.execute('PRAGMA table_info(AppSettings)')
print('AppSettings columns:', cursor.fetchall())
cursor.execute('SELECT * FROM AppSettings')
print('AppSettings data:', cursor.fetchall())
