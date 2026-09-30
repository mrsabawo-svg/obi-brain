"""Produce conservative OBI market snapshots for the dashboard and alert bot."""

import json
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import yfinance as yf
from hmmlearn.hmm import GaussianHMM

warnings.filterwarnings("ignore")

SYMBOLS = {"XAUUSD": "GC=F", "EURUSD": "EURUSD=X", "BTCUSD": "BTC-USD"}
OUTPUT_FILE = Path(__file__).with_name("output.json")
LOOKBACK_BARS = 100
N_REGIMES = 3
KELLY_FRACTION = 0.5


def label_regimes(model):
    """Label the otherwise anonymous HMM states by their volatility."""
    volatility_rank = np.argsort(np.sqrt(model.covars_.reshape(-1)))
    return {
        int(volatility_rank[0]): "RANGING",
        int(volatility_rank[1]): "TRENDING",
        int(volatility_rank[2]): "VOLATILE",
    }


def compute_obi(closes, volumes):
    """Return a simple 0--100 up-volume imbalance and its direction."""
    if len(closes) < 20 or len(volumes) < 20:
        return 50.0, "NEUTRAL"

    recent_closes, recent_volumes = closes[-20:], volumes[-20:]
    buy_volume = sum(v for i, v in enumerate(recent_volumes[1:]) if recent_closes[i + 1] > recent_closes[i])
    sell_volume = sum(v for i, v in enumerate(recent_volumes[1:]) if recent_closes[i + 1] < recent_closes[i])
    total_volume = buy_volume + sell_volume
    if total_volume <= 0:
        return 50.0, "NEUTRAL"

    score = round(float(buy_volume / total_volume * 100), 1)
    direction = "BULLISH" if score > 62 else "BEARISH" if score < 38 else "NEUTRAL"
    return score, direction


def compute_kelly(win_rate, avg_win, avg_loss):
    """Return a capped half-Kelly fraction; never recommend a negative size."""
    if avg_loss <= 0:
        return 0.0
    odds = avg_win / avg_loss
    full_kelly = (odds * win_rate - (1 - win_rate)) / odds
    return round(min(max(0.0, full_kelly * KELLY_FRACTION), 0.02), 4)


def derive_sentiment(regime, obi_direction):
    if regime == "VOLATILE":
        return "STAND ASIDE"
    if regime == "TRENDING" and obi_direction == "BULLISH":
        return "BULLISH BIAS - LOOK TO BUY"
    if regime == "TRENDING" and obi_direction == "BEARISH":
        return "BEARISH BIAS - LOOK TO SELL"
    if regime == "RANGING" and obi_direction == "BULLISH":
        return "RANGE BUY - NEAR SUPPORT ONLY"
    if regime == "RANGING" and obi_direction == "BEARISH":
        return "RANGE SELL - NEAR RESISTANCE ONLY"
    return "WAIT FOR CLARITY"


def analyse_symbol(name, ticker_symbol):
    """Fetch and analyse one symbol, returning an error payload on failure."""
    try:
        history = yf.Ticker(ticker_symbol).history(period="5d", interval="15m")
        if history is None or len(history) < max(30, N_REGIMES + 1):
            raise ValueError("Not enough price data")
        closes = history["Close"].to_numpy(dtype=float)
        volumes = history["Volume"].to_numpy(dtype=float)
        returns = np.diff(np.log(closes)).reshape(-1, 1)
        training_returns = returns[-LOOKBACK_BARS:]
        if len(training_returns) < N_REGIMES:
            raise ValueError("Not enough returns for regime model")

        model = GaussianHMM(n_components=N_REGIMES, covariance_type="full", n_iter=100, random_state=42)
        model.fit(training_returns)
        states = model.predict(training_returns)
        regimes = label_regimes(model)
        regime = regimes[int(states[-1])]
        obi_score, obi_direction = compute_obi(closes, volumes)

        price_changes = np.diff(closes[-50:])
        wins, losses = price_changes[price_changes > 0], -price_changes[price_changes < 0]
        win_rate = float(len(wins) / len(price_changes)) if len(price_changes) else 0.0
        kelly = compute_kelly(win_rate, float(np.mean(wins)) if len(wins) else 0.0, float(np.mean(losses)) if len(losses) else 0.0)
        confidence = round(float(np.mean(states[-min(20, len(states)):] == states[-1]) * 100), 1)
        price, previous_price = float(closes[-1]), float(closes[-2])
        decimals = 2 if name == "BTCUSD" else 5
        return {
            "symbol": name, "price": round(price, decimals), "change": round(price - previous_price, decimals),
            "change_pct": round((price - previous_price) / previous_price * 100, 3), "regime": regime,
            "obi_score": obi_score, "obi_direction": obi_direction, "kelly_size": kelly,
            "confidence": confidence, "win_rate": round(win_rate * 100, 1),
            "sentiment": derive_sentiment(regime, obi_direction),
            "last_updated": datetime.now(timezone.utc).isoformat(), "status": "ok",
        }
    except Exception as error:
        return {"symbol": name, "status": "error", "error": str(error), "last_updated": datetime.now(timezone.utc).isoformat()}


def run_once(output_file=OUTPUT_FILE):
    """Write one complete, atomically replaced snapshot and return it."""
    output_file = Path(output_file)
    results = {name: analyse_symbol(name, ticker) for name, ticker in SYMBOLS.items()}
    payload = {"generated_at": datetime.now(timezone.utc).isoformat(), "symbols": results}
    temporary_file = output_file.with_suffix(".tmp")
    temporary_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    temporary_file.replace(output_file)
    return payload


def run(interval=60):
    while True:
        run_once()
        time.sleep(interval)


if __name__ == "__main__":
    run()
