import re

# App.jsx: unused 'e'
with open('frontend/src/App.jsx', 'r') as f:
    app_content = f.read()

app_content = app_content.replace('catch (e) {', 'catch {')
with open('frontend/src/App.jsx', 'w') as f:
    f.write(app_content)

# AdminPanel.jsx: unused 'Icon'
with open('frontend/src/components/AdminPanel.jsx', 'r') as f:
    admin_content = f.read()

admin_content = admin_content.replace('].map(({ id, label, icon: Icon, count }) => (', '].map(({ id, label, count }) => (')

with open('frontend/src/components/AdminPanel.jsx', 'w') as f:
    f.write(admin_content)
