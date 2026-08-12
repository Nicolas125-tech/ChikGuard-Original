import json

title = "⚡ Bolt: Fix sequential network waterfall in ClimatePanel"
description = """* 💡 What: Replaced sequential fetch polling in loadAll with concurrent Promise.all fetching.
* 🎯 Why: Fixes a network waterfall where fetchDevices, fetchHistory, and fetchWeather were executed sequentially without awaiting each other, queuing in the microtask queue and delaying initial data load time.
* 📊 Impact: Significantly reduces initial data render time by performing network requests concurrently.
* 🔬 Measurement: Verify Network tab in devtools on ClimatePanel load to see parallel execution."""

with open('payload.json', 'w') as f:
    json.dump({"title": title, "description": description}, f)
