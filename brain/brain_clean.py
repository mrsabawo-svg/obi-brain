# © 2026 Mazvita Sabawo. All rights reserved.

# OBI Intelligence Brain - runs every 60s, writes output.json

import json
import time
import numpy as np
from datetime import datetime, timezone
import yfinance as yf
from hmmlearn.hmm import GaussianHMM
import warnings
warnings.filterwarnings(‘ignore’)

SYMBOLS = {
‘XAUUSD’: ‘GC=F’,
‘EURUSD’: ‘EURUSD=X’,
‘BTCUSD’: ‘BTC-USD’
}

OUTPUT_FILE = ‘output.json’
LOOKBACK_BARS = 100
N_REGIMES = 3
KELLY_FRACTION = 0.5

def label_regimes(model):
covars = np.sqrt(model.covars_.flatten())
vol_rank = np.argsort(covars)
labels = {}
labels[vol_rank[0]] = ‘RANGING’
labels[vol_rank[1]] = ‘TRENDING’
labels[vol_rank[2]] = ‘VOLATILE’
return labels

def compute_obi(closes, volumes):
if len(closes) < 20:
return 50.0, ‘NEUTRAL’
recent_closes = closes[-20:]
recent_volumes = volumes[-20:]
buy_vol = sum(v for i, v in enumerate(recent_volumes[1:]) if recent_closes[i+1] > recent_closes[i])
sell_vol = sum(v for i, v in enumerate(recent_volumes[1:]) if recent_closes[i+1] < recent_closes[i])
total = buy_vol + sell_vol
if total == 0:
return 50.0, ‘NEUTRAL’
score = (buy_vol / total) * 100
if score > 62:
direction = ‘BULLISH’
elif score < 38:
direction = ‘BEARISH’
else:
direction = ‘NEUTRAL’
return round(score, 1), direction

def compute_kelly(win_rate, avg_win, avg_loss):
if avg_loss == 0:
return 0.0
b = avg_win / avg_loss
q = 1 - win_rate
kelly = (b * win_rate - q) / b
half_kelly = max(0.0, kelly * KELLY_FRACTION)
return round(min(half_kelly, 0.02), 4)

def derive_sentiment(regime, obi):
if regime == ‘VOLATILE’:
return ‘STAND ASIDE’
if regime == ‘TRENDING’ and obi == ‘BULLISH’:
return ‘BULLISH BIAS - LOOK TO BUY’
if regime == ‘TRENDING’ and obi == ‘BEARISH’:
return ‘BEARISH BIAS - LOOK TO SELL’
if regime == ‘RANGING’ and obi == ‘BULLISH’:
return ‘RANGE BUY - NEAR SUPPORT ONLY’
if regime == ‘RANGING’ and obi == ‘BEARISH’:
return ‘RANGE SELL - NEAR RESISTANCE ONLY’
return ‘WAIT FOR CLARITY’

def analyse_symbol(name, ticker_str):
try:
ticker = yf.Ticker(ticker_str)
df = ticker.history(period=‘5d’, interval=‘15m’)
if df is None or len(df) < 30:
raise ValueError(‘Not enough data’)
closes = df[‘Close’].values.astype(float)
volumes = df[‘Volume’].values.astype(float)
returns = np.diff(np.log(closes)).reshape(-1, 1)
model = GaussianHMM(n_components=N_REGIMES, covariance_type=‘full’, n_iter=100, random_state=42)
model.fit(returns[-LOOKBACK_BARS:])
state_seq = model.predict(returns[-LOOKBACK_BARS:])
current_state = int(state_seq[-1])
regime_map = label_regimes(model)
regime = regime_map[current_state]
obi_score, obi_direction = compute_obi(closes, volumes)
wins = sum(1 for i in range(1, min(50, len(closes))) if closes[i] > closes[i-1])
win_rate = wins / min(50, len(closes) - 1)
avg_win = np.mean([abs(closes[i] - closes[i-1]) for i in range(1, min(50, len(closes))) if closes[i] > closes[i-1]] or [0.001])
avg_loss = np.mean([abs(closes[i] - closes[i-1]) for i in range(1, min(50, len(closes))) if closes[i] < closes[i-1]] or [0.001])
kelly = compute_kelly(win_rate, avg_win, avg_loss)
regime_counts = {v: 0 for v in regime_map.values()}
for s in state_seq[-20:]:
regime_counts[regime_map[s]] += 1
confidence = round((regime_counts[regime] / 20) * 100, 1)
price = float(closes[-1])
prev_close = float(closes[-2]) if len(closes) > 1 else price
change = price - prev_close
change_pct = (change / prev_close) * 100
sentiment = derive_sentiment(regime, obi_direction)
return {
‘symbol’: name,
‘price’: round(price, 5 if ‘USD’ in name and name != ‘BTCUSD’ else 2),
‘change’: round(change, 5 if ‘USD’ in name and name != ‘BTCUSD’ else 2),
‘change_pct’: round(change_pct, 3),
‘regime’: regime,
‘obi_score’: obi_score,
‘obi_direction’: obi_direction,
‘kelly_size’: kelly,
‘confidence’: confidence,
‘win_rate’: round(win_rate * 100, 1),
‘sentiment’: sentiment,
‘last_updated’: datetime.now(timezone.utc).isoformat(),
‘status’: ‘ok’
}
except Exception as e:
return {
‘symbol’: name,
‘status’: ‘error’,
‘error’: str(e),
‘last_updated’: datetime.now(timezone.utc).isoformat()
}

def run():
print(‘OBI Brain starting…’)
while True:
print(’\n[’ + datetime.now().strftime(’%H:%M:%S’) + ‘] Running analysis…’)
results = {}
for name, ticker in SYMBOLS.items():
print(’  Analysing ’ + name + ‘…’)
results[name] = analyse_symbol(name, ticker)
r = results[name]
print(’  -> ’ + r.get(‘regime’,’?’) + ’ | OBI: ’ + r.get(‘obi_direction’,’?’) + ’ | ’ + r.get(‘sentiment’,’?’))
output = {
‘generated_at’: datetime.now(timezone.utc).isoformat(),
‘symbols’: results
}
with open(OUTPUT_FILE, ‘w’) as f:
json.dump(output, f, indent=2)
print(’  output.json written. Next run in 60s…’)
time.sleep(60)

if **name** == ‘**main**’:
run()
