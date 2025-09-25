with open(r'c:\Users\ifernandez\Desktop\script python\progetto jira timer tracker\controllers\jira_detail_controller.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix line 987: add indentation
if 987 <= len(lines):
    lines[987] = '            ' + lines[987].lstrip()

# Fix the corrupted character on line 994
if 994 <= len(lines):
    lines[994] = '            attachment_widget.thumbnail_label.setText("📄")\n'

# Write back
with open(r'c:\Users\ifernandez\Desktop\script python\progetto jira timer tracker\controllers\jira_detail_controller.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('Fixed indentation and document icon')