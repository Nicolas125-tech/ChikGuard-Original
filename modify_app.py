import re

file_path = "backend/app_flask_legacy.py"
with open(file_path, "r") as f:
    content = f.read()

# The code to replace
old_code = """            # Delete one by one to respect ORM cascades and events
            old_records = ModelClass.query.filter(ModelClass.timestamp < cutoff).all()
            if not old_records:
                continue

            count = len(old_records)
            for record in old_records:
                db.session.delete(record)
            total_deleted += count"""

# The new optimized code
new_code = """            # Optimized: delete using a single query instead of N+1
            count = ModelClass.query.filter(ModelClass.timestamp < cutoff).delete(synchronize_session=False)
            if count == 0:
                continue

            total_deleted += count"""

if old_code in content:
    content = content.replace(old_code, new_code)
    with open(file_path, "w") as f:
        f.write(content)
    print("Optimization applied successfully.")
else:
    print("Could not find the target code to replace.")
