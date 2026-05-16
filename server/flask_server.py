# “””
OBI Flask Server

Serves output.json as a public JSON API endpoint.
Deploy on PythonAnywhere — dashboard reads from this URL.

Endpoint: GET /api/signals
“””

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import json
import os

app = Flask(**name**)
CORS(app)  # Allow dashboard to read from any origin

OUTPUT_FILE = os.path.join(os.path.dirname(**file**), “..”, “brain”, “output.json”)

@app.route(”/”)
def index():
return jsonify({
“service”: “OBI Intelligence Brain”,
“status”: “running”,
“endpoints”: {
“signals”: “/api/signals”,
“health”: “/api/health”
}
})

@app.route(”/api/signals”)
def get_signals():
“”“Main endpoint — returns full signal data for all symbols.”””
try:
with open(OUTPUT_FILE, “r”) as f:
data = json.load(f)
return jsonify(data)
except FileNotFoundError:
return jsonify({
“error”: “output.json not found — brain may not have run yet”,
“symbols”: {}
}), 404
except Exception as e:
return jsonify({“error”: str(e)}), 500

@app.route(”/api/signals/<symbol>”)
def get_symbol(symbol):
“”“Get signals for a specific symbol e.g. /api/signals/XAUUSD”””
try:
with open(OUTPUT_FILE, “r”) as f:
data = json.load(f)
symbol = symbol.upper()
if symbol in data.get(“symbols”, {}):
return jsonify(data[“symbols”][symbol])
else:
return jsonify({“error”: f”{symbol} not found”}), 404
except Exception as e:
return jsonify({“error”: str(e)}), 500

@app.route(”/api/health”)
def health():
return jsonify({“status”: “ok”})

# ── PythonAnywhere entry point ────────────────────────────────

# PythonAnywhere looks for a variable called `application`

application = app

if **name** == “**main**”:
app.run(debug=False, port=5000)
