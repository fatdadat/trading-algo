import pandas as pd
from dataclasses import dataclass
from datetime import datetime
from indicators import rsi, bollinger_bands

@dataclass
class Trade:
    pair: str
    entry_time: datetime
    entry_price: float
    exit_time: datetime
    exit_price: float
    pnl: float
    fees: float

# Use OHLCV dataframe from ccxt as data input and JSON config file as input in live build
# Figure out position sizing later
class MeanReversionStrat:
    def __init__(self, config, pos = 0, pos_size = 0, trades = []):
        self.config = config
        self.pos = pos
        self.pos_size = pos_size
        self.trades = trades

    # For both entry and exit signals, could combine into seperate functions in future
    def gen_signal(self, data):
        rsi = rsi(data, period=self.config['strategy']['rsi_period'])
        bb_upper, bb_middle, bb_lower = bollinger_bands(data, period=self.config['bb_period'], std_dev=self.config['bb_std_dev'])
        rsi_oversold = self.config['strategy']['rsi_oversold']
        rsi_overbought = self.config['strategy']['rsi_overbought']

        cur_price = data.iloc[-1]['close']

        if self.pos == 0: #Check for entry signal
            # Buy signal
            if rsi < rsi_oversold and cur_price < bb_lower:
                return 1
            # Sell signal
            elif rsi > rsi_overbought and cur_price > bb_upper:
                return -1
            
        elif self.pos != 0: #Check for exit signal
            # Exit long buy selling when <= lower BB
            if self.pos == 1 and rsi <= bb_lower:
                return -1
            elif self.pos == -1 and rsi >= bb_upper:
                return 1
        
        # No signal
        return 0
    
    def enter_position(self, signal):
        pass

    def execute_trade(self, signal):
        pass

    def record_trade(self):
        pass

    def save_trade(self, trade: Trade, filename: str):
        pass
    
    

