import ccxt
import pandas as pd

class APIClient:
    def __init__(self, config, api_key, api_secret):
        #since ccxt.'binance' doesn't work
        self.exchange = getattr(ccxt, config['trading']['exchange'])({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True
        }) 
        self.config = config

    def fetch_ohlcv_df(self, symbol):
        #time of each candlestick
        timeframe = self.config['trading']['timeframe']

        #number of candlesticks
        period = self.config['trading']['period']

        try:
            data = self.exchange.fetch_ohlcv(symbol, timeframe, limit=period)
            ohlcv_df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            ohlcv_df['timestamp'] = pd.to_datetime(ohlcv_df['timestamp'], unit = 'ms')
            return ohlcv_df
        
        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")
            return None
        
    # def create_order(self, symbol, side, amount):
    #     try:
    #         order = self.exchange.create_order(symbol=symbol, type='market', side=side, amount=amount)
    #         return order
        
    #     except Exception as e:
    #         print(f"Error creating order for {symbol}: {e}")
    #         return None
        
    # # returns a dictionary with the balance of each currency for 'total', 'free' and 'used'
    # def fetch_balance(self):
    #     try:
    #         balance = self.exchange.fetch_balance()
    #         return balance
        
    #     except Exception as e:
    #         print(f"Error fetching balance: {e}")
    #         return None
        
    # def fetch_positions(self):
    #     try:
    #         positions = self.exchange.fetch_positions()
    #         return positions
        
    #     except Exception as e:
    #         print(f"Error fetching positions: {e}")
    #         return None
        

        

        



