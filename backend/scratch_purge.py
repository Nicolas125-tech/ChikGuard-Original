import re

with open('c:/nic/ChikGuard-Original/backend/app.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Remove _simulate_acoustic_analysis definition and its calls
code = re.sub(r'\ndef _simulate_acoustic_analysis\(\):.*?last_acoustic_save_ts = now\n', '', code, flags=re.DOTALL)
code = re.sub(r'\s*_simulate_acoustic_analysis\(\)\n', '\n', code)

# Remove _simulate_sensor_updates definition and its calls
code = re.sub(r'\ndef _simulate_sensor_updates\(temp_atual\):.*?_evaluate_sensor_alerts\(\)\n', '', code, flags=re.DOTALL)
code = re.sub(r'\s*_simulate_sensor_updates\(temp_atual\)\n', '\n', code)

# Remove _simulate_airflow_field definition and its calls
code = re.sub(r'\ndef _simulate_airflow_field\(fans=None, grid_size=24\):.*?\s+return \{\n.*?\]\n\s+\}\n', '', code, flags=re.DOTALL)

# Remove /api/airflow/simulate route
code = re.sub(r'\n@app\.route\("/api/airflow/simulate", methods=\["POST"\]\).*?def airflow_simulate\(\):.*?return jsonify\(result\)\n', '', code, flags=re.DOTALL)

# Remove random import
code = re.sub(r'import random\n', '', code)

# Fix missing/trailing sources
code = code.replace('            "source": "simulated_fallback",\n', '')
code = code.replace('"source": "simulated",', '"source": "sensor",')
code = code.replace('_persist_sensor_reading(source="simulated")', '_persist_sensor_reading(source="sensor")')
code = code.replace('    "source": "simulated",', '    "source": "sensor",')

with open('c:/nic/ChikGuard-Original/backend/app.py', 'w', encoding='utf-8') as f:
    f.write(code)
