#Infinite while loop here
import os
import sys
from pathlib import Path

# Get the absolute path to the project root
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

# sys.path.append('..')

import json
from utilities.api_client import APIClient
from keys import API_KEY, API_SECRET

from strategies.indicators import rsi, bb, atr, std_dev
from strategies.mean_reversion import MeanReversionStrat

with open('config.json', 'r') as f:
    config = json.load(f)

client = APIClient(config, API_KEY, API_SECRET)
print(client.exchange.fetch_ticker('BTC/USDT'))
print(client.exchange.fetch_balance()['BTC']['free'])
print("\nFREE AUD BALANCE:", client.exchange.fetch_balance()['AUD']['free'])
# strategy = MeanReversionStrat(config=config, balance=client.exchange.fetch_balance()['BTC']['free'])



data = client.fetch_ohlcv_df('BTC/USDT')
print(data)

rsi(data, 14)
atr(data, 14)

upper, middle, lower = bb(data, config['strategy']['bollinger_period'], config['strategy']['bollinger_std_dev'])

# surprisingly close in value
print(std_dev(data, 14))
print(atr(data, 14))

print('entry from middle',upper-middle)
# print('sl from middle', strategy.sl_dist(signal = 1, data = data))

print('bid',client.fetch_bid('BTC/USDT'))
print('ask',client.fetch_ask('BTC/USDT'))