
import requests
import pandas as pd
import numpy as np
from datetime import datetime
import time
from flask import Flask, render_template_string
from threading import Thread
import json
import os
# Telegram config
TELEGRAM_BOT_TOKEN = '7693632069:AAGVgnFYxg8m_1gePIpUet9XkEF_F5ZkKNI'
TELEGRAM_CHAT_ID = '1962340625'

# HTML Template for Flask
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang=\"en\">
<head>
    <meta charset=\"UTF-8\">
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

# All other code remains unchanged...
