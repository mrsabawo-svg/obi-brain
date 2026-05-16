# “””
OBI Intelligence Brain

Runs every 60 seconds, fetches price data,
computes HMM regime, OBI score, Kelly size,
and writes output.json for the dashboard + Telegram bot.

Free data source: Yahoo Finance (yfinance) - no API key needed
“””

import json
import time
import os
import numpy as np
from datetime import datetime, timezone
import yfinance as yf
from hmmlearn.hmm import GaussianHMM
import warnings
warnings.filterwarnings(“ignore”)

# ── Config ────────────────────────────────────────────────────

SYMBOLS = {
“XAUUSD”: “GC=F”,     # Gold futures (proxy for XAUUSD)
“EURUSD”: “EURUSD=X”,  # EUR/USD
“BTCUSD”: “BTC-USD”    # Bitcoin
}

OUTPUT_FILE = “output.json”
LOOKBACK_BARS = 100       # bars used for HMM training
N_REGIMES = 3             # Trending, Ranging, Volatile
KELLY_FRACTION = 0.5      # Half-Kelly

# ── Regime Labels ─────────────────────────────────────────────

# HMM states are unlabeled — we label by volatility rank

# State with lowest vol  = RANGING

# State with highest vol = VOLATILE

# Middle state           = TRENDING

def label_regimes(model, n_states=3):
“”“Map HMM state indices to human labels based on volatility.”””
means = model.means_.flatten()
covars = np.sqrt(model.covars_.flatten())
vol_rank = np.argsort(covars)
labels = {}
labels[vol_rank[0]] = “RANGING”
labels[vol_rank[1]] = “TRENDING”
labels[vol_rank[2]] = “VOLATILE”
return labels

# ── OBI Score ─────────────────────────────────────────────────

def compute_obi(closes, volumes):
“””
Simplified OBI: compare up-volume vs down-volume over last 20 bars.
Returns score 0-100 and direction label.
“””
if len(closes) < 20:
return 50.0, “NEUTRAL”

```
recent_closes = closes[-20:]
recent_volumes = volumes[-20:]

buy_vol = sum(v for i, v in enumerate(recent_volumes[1:])
              if recent_closes[i+1] > recent_closes[i])
sell_vol = sum(v for i, v in enumerate(recent_volumes[1:])
               if recent_closes[i+1] < recent_closes[i])
total = buy_vol + sell_vol

if total == 0:
    return 50.0, "NEUTRAL"

score = (buy_vol / total) * 100

if score > 62:
    direction = "BULLISH"
elif score < 38:
    direction = "BEARISH"
else:
    direction = "NEUTRAL"

return round(score, 1), direction
```

# ── Kelly Sizing ──────────────────────────────────────────────

def compute_kelly(win_rate, avg_win, avg_loss):
“”“Half-Kelly position sizing.”””
if avg_loss == 0:
return 0.0
b = avg_win / avg_loss
q = 1 - win_rate
kelly = (b * win_rate - q) / b
half_kelly = max(0.0, kelly * KELLY_FRACTION)
return round(min(half_kelly, 0.02), 4)  # cap at 2%

# ── Fetch & Analyse One Symbol ────────────────────────────────

def analyse_symbol(name, ticker_str):
try:
ticker = yf.Ticker(ticker_str)
df = ticker.history(period=“5d”, interval=“15m”)

```
    if df is None or len(df) < 30:
        raise ValueError("Not enough data")

    closes = df["Close"].values.astype(float)
    volumes = df["Volume"].values.astype(float)
    highs = df["High"].values.astype(float)
    lows = df["Low"].values.astype(float)

    # Returns for HMM
    returns = np.diff(np.log(closes)).reshape(-1, 1)

    # ── HMM Regime ──
    model = GaussianHMM(
        n_components=N_REGIMES,
        covariance_type="full",
        n_iter=100,
        random_state=42
    )
    model.fit(returns[-LOOKBACK_BARS:])
    state_seq = model.predict(returns[-LOOKBACK_BARS:])
    current_state = int(state_seq[-1])
    regime_map = label_regimes(model)
    regime = regime_map[current_state]

    # ── OBI ──
    obi_score, obi_direction = compute_obi(closes, volumes)

    # ── Simple Win Rate from last 50 bars ──
    wins = sum(1 for i in range(1, min(50, len(closes)))
               if closes[i] > closes[i-1])
    win_rate = wins / min(50, len(closes) - 1)
    avg_win = np.mean([abs(closes[i] - closes[i-1])
                       for i in range(1, min(50, len(closes)))
                       if closes[i] > closes[i-1]] or [0.001])
    avg_loss = np.mean([abs(closes[i] - closes[i-1])
                        for i in range(1, min(50, len(closes)))
                        if closes[i] < closes[i-1]] or [0.001])

    kelly = compute_kelly(win_rate, avg_win, avg_loss)

    # ── Confidence (simple: how dominant is current regime) ──
    regime_counts = {v: 0 for v in regime_map.values()}
    for s in state_seq[-20:]:
        regime_counts[regime_map[s]] += 1
    confidence = round((regime_counts[regime] / 20) * 100, 1)

    # ── Price info ──
    price = float(closes[-1])
    prev_close = float(closes[-2]) if len(closes) > 1 else price
    change = price - prev_close
    change_pct = (change / prev_close) * 100

    # ── Sentiment ──
    sentiment = derive_sentiment(regime, obi_direction)

    return {
        "symbol": name,
        "price": round(price, 5 if "USD" in name and name != "BTCUSD" else 2),
        "change": round(change, 5 if "USD" in name and name != "BTCUSD" else 2),
        "change_pct": round(change_pct, 3),
        "regime": regime,
        "obi_score": obi_score,
        "obi_direction": obi_direction,
        "kelly_size": kelly,
        "confidence": confidence,
        "win_rate": round(win_rate * 100, 1),
        "sentiment": sentiment,
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "status": "ok"
    }

except Exception as e:
    return {
        "symbol": name,
        "status": "error",
        "error": str(e),
        "last_updated": datetime.now(timezone.utc).isoformat()
    }
```

# ── Sentiment Logic ───────────────────────────────────────────

def derive_sentiment(regime, obi):
if regime == “VOLATILE”:
return “STAND ASIDE”
if regime == “TRENDING” and obi == “BULLISH”:
return “BULLISH BIAS — LOOK TO BUY”
if regime == “TRENDING” and obi == “BEARISH”:
return “BEARISH BIAS — LOOK TO SELL”
if regime == “RANGING” and obi == “BULLISH”:
return “RANGE BUY — NEAR SUPPORT ONLY”
if regime == “RANGING” and obi == “BEARISH”:
return “RANGE SELL — NEAR RESISTANCE ONLY”
return “WAIT FOR CLARITY”

# ── Main Loop ─────────────────────────────────────────────────

def run():
print(“OBI Brain starting…”)
while True:
print(f”\n[{datetime.now().strftime(’%H:%M:%S’)}] Running analysis…”)
results = {}
for name, ticker in SYMBOLS.items():
print(f”  Analysing {name}…”)
results[name] = analyse_symbol(name, ticker)
print(f”  → {results[name].get(‘regime’,’?’)} | OBI: {results[name].get(‘obi_direction’,’?’)} | {results[name].get(‘sentiment’,’?’)}”)

```
    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "symbols": results
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)

    print(f"  ✓ output.json written")
    print(f"  Next run in 60 seconds...")
    time.sleep(60)
```

if **name** == “**main**”:
run()
