import requests
import pandas as pd
import numpy as np
from datetime import datetime
import time
from flask import Flask, render_template_string
from threading import Thread
import os

# Telegram config (in code as requested)
TELEGRAM_BOT_TOKEN = '7693632069:AAGVgnFYxg8m_1gePIpUet9XkEF_F5ZkKNI'
TELEGRAM_CHAT_ID = '1962340625'

# HTML Template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Solana Trading Bot</title>
</head>
<body>
    <h1>Solana EUR Trading Dashboard</h1>
    <p><strong>Current Price:</strong> €{{ price }}</p>
    <p><strong>RSI:</strong> {{ rsi }}</p>
    <p><strong>MACD:</strong> {{ macd }}</p>
    <p><strong>Signal:</strong> {{ signal }}</p>
    <p><strong>Last Updated:</strong> {{ time }}</p>
</body>
</html>
"""

app = Flask(__name__)
latest_data = {'price': 0, 'rsi': 0, 'macd': 0, 'signal': '⏳ HOLD', 'time': datetime.now()}

@app.route("/")
def dashboard():
    return render_template_string(HTML_TEMPLATE, **latest_data)

@app.route("/ping")
def ping():
    return "pong", 200

def calculate_rsi(data, window=14):
    delta = data.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window).mean()
    avg_loss = loss.rolling(window).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def calculate_macd(data, slow=26, fast=12, signal=9):
    exp1 = data.ewm(span=fast, adjust=False).mean()
    exp2 = data.ewm(span=slow, adjust=False).mean()
    macd = exp1 - exp2
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    return macd, signal_line

def calculate_bollinger_bands(data, window=20):
    sma = data.rolling(window).mean()
    std = data.rolling(window).std()
    upper_band = sma + 2 * std
    lower_band = sma - 2 * std
    return upper_band, lower_band

def calculate_stochastic_rsi(data, rsi_window=14, stoch_window=14):
    rsi = calculate_rsi(data, window=rsi_window)
    stoch_rsi = (rsi - rsi.rolling(stoch_window).min()) / (rsi.rolling(stoch_window).max() - rsi.rolling(stoch_window).min())
    return stoch_rsi * 100

def calculate_obv(data):
    data['volume'] = 1
    obv = [0]
    for i in range(1, len(data)):
        if data['price'].iloc[i] > data['price'].iloc[i - 1]:
            obv.append(obv[-1] + data['volume'].iloc[i])
        elif data['price'].iloc[i] < data['price'].iloc[i - 1]:
            obv.append(obv[-1] - data['volume'].iloc[i])
        else:
            obv.append(obv[-1])
    return pd.Series(obv, index=data.index)

def fetch_btc_dominance():
    try:
        url = "https://api.coingecko.com/api/v3/global"
        response = requests.get(url)
        return response.json()['data']['market_cap_percentage']['btc']
    except:
        return None

def fetch_ohlc_data():
    url = "https://api.coingecko.com/api/v3/coins/solana/ohlc"
    params = {"vs_currency": "eur", "days": "1"}
    try:
        response = requests.get(url, params=params)
        data = response.json()
        df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        df.rename(columns={'close': 'price'}, inplace=True)
        return df[['price']]
    except:
        return None

def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    requests.post(url, data=data)

def run_bot():
    while True:
        df = fetch_ohlc_data()
        if df is not None:
            df['RSI'] = calculate_rsi(df['price'])
            df['MACD'], df['MACD_signal'] = calculate_macd(df['price'])
            df['Upper_BB'], df['Lower_BB'] = calculate_bollinger_bands(df['price'])
            df['Stoch_RSI'] = calculate_stochastic_rsi(df['price'])
            df['OBV'] = calculate_obv(df)
            df['Short_MA'] = df['price'].rolling(window=5).mean()
            df['Long_MA'] = df['price'].rolling(window=20).mean()
            df['peak'] = df['price'].cummax()
            trailing_stop = df['peak'].iloc[-1] * 0.97
            btc_dominance = fetch_btc_dominance()

            rsi = df['RSI'].iloc[-1]
            macd = df['MACD'].iloc[-1]
            signal = "⏳ HOLD"

            message = message = (
                          f"📊 SOL Trading Signal - {signal}\n"
                          f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                          f"Price: €{df['price'].iloc[-1]:.2f}\n"
                          f"Signal: {signal}\n"
                          f"RSI: {rsi:.2f} (30–70 = neutral, <30 = oversold, >70 = overbought)\n"
                          f"MACD: {macd:.2f} (MACD > Signal = bullish momentum)\n"
                          f"MACD Signal: {df['MACD_signal'].iloc[-1]:.2f}\n"
                          f"StochRSI: {df['Stoch_RSI'].iloc[-1]:.2f} (<20 = oversold, >80 = overbought)\n"
                          f"OBV: {df['OBV'].iloc[-1]:.2f} (rising = bullish, falling = bearish)\n"
                          f"Upper BB: {df['Upper_BB'].iloc[-1]:.2f}\n"
                          f"Lower BB: {df['Lower_BB'].iloc[-1]:.2f}\n"
                          f"Short MA: {df['Short_MA'].iloc[-1]:.2f}\n"
                          f"Long MA: {df['Long_MA'].iloc[-1]:.2f}\n"
                          f"Trailing Stop: {df['peak'].iloc[-1]*0.97:.2f}\n"
                          f"BTC Dominance: {btc_dominance:.2f}% (<50 = altcoin-friendly)"
                      )
            send_telegram_alert(message)

            latest_data.update({
                'price': f"{df['price'].iloc[-1]:.2f}",
                'rsi': f"{rsi:.2f}",
                'macd': f"{macd:.2f}",
                'signal': signal,
                'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
        time.sleep(300)

# Start bot and web server
Thread(target=run_bot).start()
app.run(host="0.0.0.0", port=5050)
