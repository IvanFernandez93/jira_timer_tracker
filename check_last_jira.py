import sqlite3
conn = sqlite3.connect('C:/Users/ifernandez/AppData/Roaming/JiraTimeTracker/JiraTimeTracker/jira_tracker.db')
cursor = conn.cursor()
cursor.execute("SELECT value FROM AppSettings WHERE key='last_active_jira'")
result = cursor.fetchone()
if result:
    print('Last Active Jira:', result[0])
else:
    print('No last active Jira found')
conn.close()