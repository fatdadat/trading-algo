import pandas as pd
from dataclasses import dataclass
from datetime import datetime
from .indicators import rsi, bb, atr, std_dev

@dataclass
# Should i make it a trade that has closed? idk
class Trade:
    id: int
    pair: str
    time: datetime
    size: float
    price: float
    fees: float
    side: str  # 'long' or 'short'


# Use OHLCV dataframe from ccxt as data input and JSON config file as input in live build
# Figure out position sizing later
class MeanReversionStrat:
    def __init__(self, config, balance, pos = 0, pos_size = 0, trades = []):
        self.config = config
        self.balance = balance
        self.pos = pos
        self.pos_size = pos_size
        self.trades = trades

    # For both entry and exit signals, could combine into seperate functions in future
    def gen_signal(self, data):
        rsi = rsi(data, period=self.config['strategy']['rsi_period'])
        bb_upper, bb_middle, bb_lower = bb(data, period=self.config['bb_period'], std_dev=self.config['bb_std_dev'])
        rsi_oversold = self.config['strategy']['rsi_oversold']
        rsi_overbought = self.config['strategy']['rsi_overbought']
        rsi_exitlong = self.config['strategy']['rsi_exitlong']
        rsi_exitsell = self.config['strategy']['rsi_exitsell']
        sma = sma(data, period=self.config['strategy']['sma_period'])

        # close price of current day is current trading price
        cur_price = data.iloc[-1]['close']

        if self.pos == 0: #Check for entry signal
            enter_long = rsi <= rsi_oversold and cur_price < bb_lower
            enter_short = rsi >= rsi_overbought and cur_price > bb_upper
            # Buy signal
            if enter_long:
                return 1
            # Sell signal
            elif enter_short:
                return -1
        # TODO: change from 2nd bb to middle bb
        elif self.pos != 0: #Check for exit signal
            long_sl_hit = cur_price >= self.trades[-1].price + self.sl_dist(signal=1, data=data)
            exit_long = (cur_price <= sma or rsi >= rsi_exitlong or long_sl_hit)

            short_sl_hit = cur_price <= self.trades[-1].price - self.sl_dist(signal=-1, data=data)
            exit_short = (cur_price >= sma or rsi <= rsi_exitsell or short_sl_hit)
            

            if self.pos == 1 and (exit_long):
                return -1
            elif self.pos == -1 and (exit_short):
                return 1
        # No signal
        return 0
    
    def sl_dist(self, signal, data):
        # TODO: change ATR multiplier later
        # Decide on volatility or ATR for sl distance measurement 
        atr_period = self.config['strategy']['atr_period']
        stop_loss_pct = self.config['risk_management']['stop_loss_pct']
        if signal == 1:
            dist = atr(data, period=atr_period)*stop_loss_pct*2

            # Std_dev to measure distance
            # dist = std_dev(data, period=self.config['strategy']['bollinger_period'])

            # Exit when lost 40% of position size
            # dist = 0.4*data.iloc[-1]['close']
        elif signal == -1:
            # lower multiplier for short (higher upside risk)
            dist = atr(data, period=atr_period)*stop_loss_pct*1.5

            # Std_dev to measure distance
            # dist = std_dev(data, period=self.config['strategy']['bollinger_period'])

            # Exit when lost 40% of position size
            # dist = 0.4*data.iloc[-1]['close']

        return dist


    
    def enter_position(self, signal, data):
        if signal == 1:
            self.pos = 1
            #figure this out later lol
            self.pos_size = self.config['risk_management']['portfolio_risk']*self.balance/self.sl_dist(signal, data)

        elif signal == -1:
            self.pos = -1
            self.pos_size = self.config['risk_management']['portfolio_risk']*self.balance/self.sl_dist(signal, data)

    def execute_trade(self, signal, data):
        self.enter_position(signal, data)
        if signal == 1:
            # TODO: add fees
            trade = Trade(id=len(self.trades)+1, pair=self.config['pair'], time=data.iloc[-1]['timestamp'], price=data.iloc[-1]['close'], fees=0)
            self.trades.append(trade)
        elif signal == -1:
            pass



    

    def record_trade(self):
        pass

    def save_trade(self, trade: Trade, filename: str):
        pass
    
    

