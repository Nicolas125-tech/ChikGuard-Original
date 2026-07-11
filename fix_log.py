import re

with open("backend/app_flask_legacy.py", "r") as f:
    content = f.read()

# Fix the _log_event parameters to exactly match original
old_log = """            message=message,
            metadata={
                "status": status,
                "dispersion_ratio": behavior_state["dispersion_ratio"],
                "edge_ratio": behavior_state["edge_ratio"],
                "count": count,
            },"""
new_log = """            message=f"Alerta IA: {status} - {message}",
            metadata={
                "count": count,
                "dispersion": round(dispersion_ratio, 2),
                "immobility": round(immobility_ratio, 2),
            },"""

content = content.replace(old_log, new_log)

with open("backend/app_flask_legacy.py", "w") as f:
    f.write(content)
