#Infinite while loop here
import os
import sys
from pathlib import Path

# Get the absolute path to the project root
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

import json
from utilities.api_client import APIClient
from keys import API_KEY, API_SECRET

with open('config.json', 'r') as f:
    config = json.load(f)

client = APIClient(config, API_KEY, API_SECRET)

data = client.fetch_ohlcv_df('BTC/USDT')
print(data)
