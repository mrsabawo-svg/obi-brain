“””
© 2026 Mazvita Sabawo. All rights reserved.

# OBI Telegram Alert Bot

Reads output.json every 60 seconds.
Sends alerts to your iPhone when:

- Regime changes
- OBI direction shifts
- High confidence trending setups appear
- News blackout windows approach

Setup:

1. Message @BotFather on Telegram → /newbot → copy token
1. Message @userinfobot on Telegram → copy your chat_id
1. Set environment variables:
   export TELEGRAM_TOKEN=“your_token_here”
   export TELEGRAM_CHAT_ID=“your_chat_id_here”
   “””

import os
import json
import time
import requests
from datetime import datetime, timezone

# ── Config ────────────────────────────────────────────────────

TOKEN = os.environ.get(“TELEGRAM_TOKEN”, “8812620780:AAGxW-tr3EKv3-I6v0vZZJSkqI9XEsOewdE”)
CHAT_ID = os.environ.get(“TELEGRAM_CHAT_ID”, “8240619659”)
OUTPUT_FILE = os.path.join(os.path.dirname(**file**), “..”, “brain”, “output.json”)
CHECK_INTERVAL = 60  # seconds

# ── State tracking (detect changes) ──────────────────────────

previous_state = {}

# ── Telegram API ──────────────────────────────────────────────

def send_message(text):
“”“Send a message to your Telegram.”””
if not TOKEN or not CHAT_ID:
print(“⚠️  No Telegram credentials. Set TELEGRAM_TOKEN and TELEGRAM_CHAT_ID”)
return
url = f”https://api.telegram.org/bot{TOKEN}/sendMessage”
payload = {
“chat_id”: CHAT_ID,
“text”: text,
“parse_mode”: “Markdown”
}
try:
r = requests.post(url, json=payload, timeout=10)
if r.status_code == 200:
print(f”  ✓ Telegram sent”)
else:
print(f”  ✗ Telegram error: {r.text}”)
except Exception as e:
print(f”  ✗ Telegram exception: {e}”)

# ── Emoji helpers ─────────────────────────────────────────────

REGIME_EMOJI = {
“TRENDING”: “📈”,
“RANGING”: “↔️”,
“VOLATILE”: “⚡”
}

OBI_EMOJI = {
“BULLISH”: “🟢”,
“BEARISH”: “🔴”,
“NEUTRAL”: “⚪”
}

SENTIMENT_EMOJI = {
“BULLISH BIAS — LOOK TO BUY”: “🚀”,
“BEARISH BIAS — LOOK TO SELL”: “🔻”,
“RANGE BUY — NEAR SUPPORT ONLY”: “📌”,
“RANGE SELL — NEAR RESISTANCE ONLY”: “📌”,
“STAND ASIDE”: “🚫”,
“WAIT FOR CLARITY”: “⏳”
}

# ── Format alert message ──────────────────────────────────────

def format_alert(symbol, data, change_type):
regime = data.get(“regime”, “?”)
obi = data.get(“obi_direction”, “?”)
sentiment = data.get(“sentiment”, “?”)
confidence = data.get(“confidence”, 0)
price = data.get(“price”, “?”)
kelly = data.get(“kelly_size”, 0)
change_pct = data.get(“change_pct”, 0)

```
r_emoji = REGIME_EMOJI.get(regime, "")
o_emoji = OBI_EMOJI.get(obi, "")
s_emoji = SENTIMENT_EMOJI.get(sentiment, "")

direction = "▲" if float(change_pct) >= 0 else "▼"

msg = f"""
```

🧠 *OBI INTELLIGENCE ALERT*
━━━━━━━━━━━━━━━━━━━━
*{symbol}* · {price} {direction}{abs(float(change_pct)):.3f}%

{r_emoji} *Regime:* {regime}
{o_emoji} *OBI:* {obi} ({data.get(‘obi_score’, ‘?’)})
📊 *Confidence:* {confidence}%
💰 *Kelly Size:* {float(kelly)*100:.2f}%

{s_emoji} *{sentiment}*
━━━━━━━━━━━━━━━━━━━━
*Trigger: {change_type}*
*{datetime.now().strftime(’%H:%M:%S’)} UTC*
“””
return msg.strip()

def format_summary():
“”“Full summary of all symbols.”””
try:
with open(OUTPUT_FILE, “r”) as f:
data = json.load(f)
except:
return “⚠️ Brain output not available yet.”

```
lines = ["🧠 *OBI MARKET SUMMARY*", "━━━━━━━━━━━━━━━━━━━━"]
for sym, d in data.get("symbols", {}).items():
    if d.get("status") == "error":
        lines.append(f"❌ *{sym}*: Error")
        continue
    r = REGIME_EMOJI.get(d.get("regime",""), "")
    o = OBI_EMOJI.get(d.get("obi_direction",""), "")
    s = SENTIMENT_EMOJI.get(d.get("sentiment",""), "")
    lines.append(
        f"{r} *{sym}* {d.get('price','?')} | {o} {d.get('obi_direction','?')} | {s} {d.get('sentiment','?')}"
    )
lines.append(f"\n_{datetime.now().strftime('%H:%M:%S')} UTC_")
return "\n".join(lines)
```

# ── Change Detection ──────────────────────────────────────────

def check_for_changes(current_data):
global previous_state
alerts = []

```
for symbol, data in current_data.get("symbols", {}).items():
    if data.get("status") == "error":
        continue

    prev = previous_state.get(symbol, {})
    changes = []

    # Regime change
    if prev.get("regime") and prev["regime"] != data["regime"]:
        changes.append(f"Regime changed: {prev['regime']} → {data['regime']}")

    # OBI direction change
    if prev.get("obi_direction") and prev["obi_direction"] != data["obi_direction"]:
        changes.append(f"OBI shifted: {prev['obi_direction']} → {data['obi_direction']}")

    # High confidence trending setup (new)
    if (data["regime"] == "TRENDING" and
        data["obi_direction"] != "NEUTRAL" and
        float(data["confidence"]) >= 70 and
        not (prev.get("regime") == "TRENDING" and
             float(prev.get("confidence", 0)) >= 70)):
        changes.append("High confidence trending setup detected")

    if changes:
        alerts.append((symbol, data, " | ".join(changes)))

    # Update state
    previous_state[symbol] = {
        "regime": data["regime"],
        "obi_direction": data["obi_direction"],
        "confidence": data["confidence"],
        "sentiment": data["sentiment"]
    }

return alerts
```

# ── Main Loop ─────────────────────────────────────────────────

def run():
print(“OBI Telegram Bot starting…”)
print(f”Checking every {CHECK_INTERVAL} seconds…\n”)

```
# Send startup message
send_message("🟢 *OBI Intelligence Bot is online*\nSend /summary for current market state.")

while True:
    try:
        with open(OUTPUT_FILE, "r") as f:
            data = json.load(f)

        alerts = check_for_changes(data)
        if alerts:
            for symbol, sym_data, change_type in alerts:
                msg = format_alert(symbol, sym_data, change_type)
                send_message(msg)
                print(f"  Alert sent: {symbol} — {change_type}")
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] No changes detected")

    except FileNotFoundError:
        print("  Waiting for output.json...")
    except Exception as e:
        print(f"  Error: {e}")

    time.sleep(CHECK_INTERVAL)
```

# ── Simple command handler (polling) ─────────────────────────

def handle_commands():
“”“Basic command polling — respond to /summary from your phone.”””
if not TOKEN:
return
last_update_id = 0
url = f”https://api.telegram.org/bot{TOKEN}/getUpdates”
try:
r = requests.get(url, params={“offset”: last_update_id, “timeout”: 5}, timeout=10)
updates = r.json().get(“result”, [])
for update in updates:
last_update_id = update[“update_id”] + 1
msg = update.get(“message”, {}).get(“text”, “”)
if msg == “/summary”:
send_message(format_summary())
elif msg == “/start”:
send_message(“🧠 *OBI Intelligence Bot*\nCommands:\n/summary — current market state”)
except:
pass

if **name** == “**main**”:
run()
