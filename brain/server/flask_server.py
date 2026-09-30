"""Compatibility entry point for deployments that reference this path."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from server.flask_server import app, application  # noqa: E402,F401


if __name__ == "__main__":
    app.run(debug=False, port=5000)
