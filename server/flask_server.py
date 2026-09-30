"""Read-only HTTP API for the OBI market snapshot."""

import json
from pathlib import Path

from flask import Flask, jsonify
from flask_cors import CORS

OUTPUT_FILE = Path(__file__).resolve().parents[1] / "brain" / "output.json"


def create_app(output_file=OUTPUT_FILE):
    app = Flask(__name__)
    CORS(app)
    snapshot_file = Path(output_file)

    def read_snapshot():
        with snapshot_file.open(encoding="utf-8") as file:
            return json.load(file)

    @app.get("/")
    def index():
        return jsonify({"service": "OBI Intelligence Brain", "status": "running", "endpoints": {"signals": "/api/signals", "health": "/api/health"}})

    @app.get("/api/signals")
    def get_signals():
        try:
            return jsonify(read_snapshot())
        except FileNotFoundError:
            return jsonify({"error": "output.json not found - brain may not have run yet", "symbols": {}}), 404
        except json.JSONDecodeError:
            return jsonify({"error": "output.json is invalid"}), 503

    @app.get("/api/signals/<symbol>")
    def get_symbol(symbol):
        try:
            signal = read_snapshot().get("symbols", {}).get(symbol.upper())
        except FileNotFoundError:
            return jsonify({"error": "output.json not found - brain may not have run yet"}), 404
        except json.JSONDecodeError:
            return jsonify({"error": "output.json is invalid"}), 503
        if signal is None:
            return jsonify({"error": f"{symbol.upper()} not found"}), 404
        return jsonify(signal)

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok", "snapshot_available": snapshot_file.is_file()})

    return app


app = create_app()
application = app

if __name__ == "__main__":
    app.run(debug=False, port=5000)
