"""Send OBI snapshot changes to Telegram when credentials are configured."""

import json
import os
import time
from datetime import datetime
from pathlib import Path

import requests

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
OUTPUT_FILE = Path(__file__).resolve().parents[1] / "output.json"
CHECK_INTERVAL = 60
previous_state = {}

REGIME_EMOJI = {"TRENDING": "📈", "RANGING": "↔️", "VOLATILE": "⚡"}
OBI_EMOJI = {"BULLISH": "🟢", "BEARISH": "🔴", "NEUTRAL": "⚪"}


def send_message(text):
    """Send a Markdown message, without ever embedding credentials in source."""
    if not TOKEN or not CHAT_ID:
        return False
    response = requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"},
        timeout=10,
    )
    return response.ok


def format_alert(symbol, data, change_type):
    change_pct = float(data.get("change_pct", 0))
    direction = "▲" if change_pct >= 0 else "▼"
    return "\n".join((
        "🧠 *OBI INTELLIGENCE ALERT*", "━━━━━━━━━━━━━━━━━━━━",
        f"*{symbol}* · {data.get('price', '?')} {direction}{abs(change_pct):.3f}%",
        f"{REGIME_EMOJI.get(data.get('regime'), '')} *Regime:* {data.get('regime', '?')}",
        f"{OBI_EMOJI.get(data.get('obi_direction'), '')} *OBI:* {data.get('obi_direction', '?')} ({data.get('obi_score', '?')})",
        f"📊 *Confidence:* {data.get('confidence', 0)}%",
        f"💰 *Kelly Size:* {float(data.get('kelly_size', 0)) * 100:.2f}%",
        f"*{data.get('sentiment', 'WAIT FOR CLARITY')}*", "━━━━━━━━━━━━━━━━━━━━",
        f"*Trigger: {change_type}*", f"*{datetime.utcnow():%H:%M:%S} UTC*",
    ))


def check_for_changes(current_data):
    alerts = []
    for symbol, data in current_data.get("symbols", {}).items():
        if data.get("status") != "ok":
            continue
        previous = previous_state.get(symbol, {})
        changes = []
        if previous.get("regime") and previous["regime"] != data.get("regime"):
            changes.append(f"Regime changed: {previous['regime']} → {data['regime']}")
        if previous.get("obi_direction") and previous["obi_direction"] != data.get("obi_direction"):
            changes.append(f"OBI shifted: {previous['obi_direction']} → {data['obi_direction']}")
        if (data.get("regime") == "TRENDING" and data.get("obi_direction") != "NEUTRAL"
                and float(data.get("confidence", 0)) >= 70 and previous.get("regime") != "TRENDING"):
            changes.append("High confidence trending setup detected")
        if changes:
            alerts.append((symbol, data, " | ".join(changes)))
        previous_state[symbol] = {key: data.get(key) for key in ("regime", "obi_direction", "confidence", "sentiment")}
    return alerts


def run():
    if not TOKEN or not CHAT_ID:
        raise RuntimeError("Set TELEGRAM_TOKEN and TELEGRAM_CHAT_ID before starting the alert bot")
    send_message("🟢 *OBI Intelligence Bot is online*")
    while True:
        try:
            with OUTPUT_FILE.open(encoding="utf-8") as file:
                alerts = check_for_changes(json.load(file))
            for symbol, data, change in alerts:
                send_message(format_alert(symbol, data, change))
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    run()
