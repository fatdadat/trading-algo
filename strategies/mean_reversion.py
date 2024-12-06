import pandas as pd
from dataclasses import dataclass
from datetime import datetime
from .indicators import rsi, bb, atr, std_dev, sma
from utilities.api_client import APIClient
import os

MAKER_FEE = 0.001
TAKER_FEE = 0.001

@dataclass
# Should i make it a trade that has closed? idk
class Trade:
    id: int
    pair: str
    time: datetime
    size: float #amnt of BTC
    price: float #BTC/AUD trade price
    fees: float
    side: str  # 'long' or 'short'

class TradingEnvironment:
    def get_current_ask(self, pair: str):
        raise NotImplementedError("Subclasses must implement this method")
    
    def get_current_bid(self, pair: str):
        raise NotImplementedError("Subclasses must implement this method")
    
    def get_current_time(self):
        raise NotImplementedError("Subclasses must implement this method")
    
    def get_current_data(self):
        raise NotImplementedError("Subclasses must implement this method")
    
    def get_balance(self):
        raise NotImplementedError("Subclasses must implement this method")
    
    def get_equity(self, pair: str='BTC/USDT', position: str='flat', pos_size: float=0):
        raise NotImplementedError("Subclasses must implement this method")
    
    def update_balance(self, amount: float):
        raise NotImplementedError("Subclasses must implement this method")
    
    def execute_trade(self, trade: Trade): # signal, amount?
        raise NotImplementedError("Subclasses must implement this method")
    
    def update_period(self):
        raise NotImplementedError("Subclasses must implement this method")
    
class LiveTradingEnvironment(TradingEnvironment):
    # uses live API client to retrieve data and balance from account
    def __init__(self, client: APIClient):
        self.client = client

    def get_current_ask(self, pair: str):
        return self.client.fetch_ask(pair)
    
    def get_current_bid(self, pair: str):
        return self.client.fetch_bid(pair)

    def get_current_time(self, pair: str):
        return self.client.fetch_ohlcv_df(pair).iloc[-1]['timestamp']
    
    def get_current_data(self, pair: str):
        return self.client.fetch_ohlcv_df(pair)
    
    def get_balance(self):
        return self.client.exchange.fetch_balance()['USDT']['free']
    
    def get_equity(self, pair: str='BTC/USDT', position: str='flat', pos_size: float=0):
        # convert base to quote, figure out better way to get price value
        # can be a negative value for margin trading
        pair_quote_bal = self.client.exchange.fetch_balance()[pair]['total']*self.get_current_bid(pair)
        return self.client.exchange.fetch_balance()['USDT']['free'] + pair_quote_bal
    
    def update_balance(self, amount: float):
        pass

    def execute_trade(self, symbol, signal, size):
        order = self.client.create_order(symbol=symbol, type='market', side=signal, amount=size, price=None)
        trade_price = float(order['price'])
        # executed_size = float(order['amount'])  # Amount of BTC traded
        fees = float(order['amount']) * float(order['price']) * TAKER_FEE  # Fees in quote currency
        time = order['timestamp']
        return trade_price, fees, time
    
    def update_period(self):
        pass

class BacktestingEnvironment(TradingEnvironment):
    # only uses historical OHLCV dataframe and inital balance
    def __init__(self, data: pd.DataFrame, initial_bal, period_length, cur_period: int = 0):
        self.data = data
        self.balance = initial_bal
        self.period_length = period_length
        # use this and take all elements from cur_period to cur_period+period_length to get current price data (with bottom row being current period data)
        self.cur_period = cur_period
        self.current_data = self.data.iloc[cur_period:cur_period+period_length]

    # estimate current ask/bid price using last close price
    def get_current_ask(self, pair: str):
        return self.current_data.iloc[-1]['close']
    
    def get_current_bid(self, pair: str):
        return self.current_data.iloc[-1]['close']
    
    def get_current_time(self):
        return self.current_data.iloc[-1]['timestamp']
    
    def get_current_data(self):
        return self.current_data
    
    def get_balance(self):
        return self.balance
    
    def get_equity(self, pair: str='BTC/USDT', position: str='flat', pos_size: float=0):
        if position == 'long':
            return self.balance + self.current_data.iloc[-1]['close']*pos_size
        elif position == 'short':
            # have to buy back to convert to USDT
            return self.balance - self.current_data.iloc[-1]['close']*pos_size
        else:
            return self.balance
    
    def update_balance(self, amount: float):
        self.balance += amount

    def execute_trade(self, symbol, signal, size):
        fees = size * self.get_current_bid(symbol) * TAKER_FEE
        time = self.get_current_time()

        if signal == 'buy':
            self.update_balance(-size * self.get_current_bid(symbol)-fees)
            trade_price = self.get_current_bid(symbol)

        elif signal == 'sell':
            self.update_balance(size * self.get_current_ask(symbol)-fees)
            trade_price = self.get_current_ask(symbol)

        return trade_price, fees, time

    def update_period(self):
        if self.cur_period + self.period_length > len(self.data):
            self.current_data = None
            # raise ValueError("No more data to update period")
        else:
            self.cur_period += 1
            self.current_data = self.data.iloc[self.cur_period:self.cur_period+self.period_length]

    

# Use OHLCV dataframe from ccxt as data input and JSON config file as input in live build
class MeanReversionStrat:
    def __init__(self, config, env_type, api_key=None, api_secret=None, initial_balance=None, data=None, pos='flat', pos_size=0, trades: list[Trade] = []):
        self.config = config
        self.pos = pos 
        self.pos_size = pos_size
        self.trades = trades

        if env_type == 'live':
            if not api_key or not api_secret:
                raise ValueError("API key and secret required for live trading")
            client = APIClient(config, api_key, api_secret)
            self.env = LiveTradingEnvironment(client)

        elif env_type == 'backtest':
            if data is None or initial_balance is None:
                raise ValueError("Historical data and initial balance required for backtesting")
            period_length = config['trading']['period']
            self.env = BacktestingEnvironment(data, initial_balance, period_length)

        else:
            raise ValueError("env_type must be either 'live' or 'backtest'")

    # For both entry and exit signals, could combine into seperate functions in future
    def gen_signal(self):
        data = self.env.get_current_data()  
        rsi_val = rsi(data, period=self.config['strategy']['rsi_period'])
        bb_upper, bb_middle, bb_lower = bb(data, period=self.config['strategy']['bollinger_period'], num_devs=self.config['strategy']['bollinger_std_dev'])
        rsi_oversold = self.config['strategy']['rsi_oversold']
        rsi_overbought = self.config['strategy']['rsi_overbought']
        rsi_exitlong = self.config['strategy']['rsi_exitlong']
        rsi_exitsell = self.config['strategy']['rsi_exitsell']
        sma_val = sma(data, period=self.config['strategy']['sma_period'])

        # close price of current day is current trading price
        cur_price = data.iloc[-1]['close']

        print('current time', self.env.get_current_time())
        print('current period', self.env.cur_period)

        if self.pos == 'flat': #Check for entry signal
            enter_long = rsi_val <= rsi_oversold and cur_price < bb_lower
            enter_short = rsi_val >= rsi_overbought and cur_price > bb_upper
            # Buy signal
            if enter_long:
                print('enter long')
                return 'buy'
            # Sell signal
            elif enter_short:
                print('enter short')
                return 'sell'

        elif self.pos == 'long': # Check for long exit signal
            long_sl_hit = cur_price >= self.trades[-1].price + self.sl_dist(signal='buy')
            exit_long = (cur_price <= sma_val or rsi_val >= rsi_exitlong or long_sl_hit)

            if exit_long:
                print('exit long')
                return 'sell'

        elif self.pos == 'short': # Check for short exit signal
            short_sl_hit = cur_price <= self.trades[-1].price - self.sl_dist(signal='sell')
            exit_short = (cur_price >= sma_val or rsi_val <= rsi_exitsell or short_sl_hit)

            if exit_short:
                print('exit short')
                return 'buy'
        # No signal
        print('no signal')
        return 'flat'
    
    def sl_dist(self, signal):
        data = self.env.get_current_data()
        # TODO: change ATR multiplier later
        # Decide on volatility or ATR for sl distance measurement 
        atr_period = self.config['strategy']['atr_period']
        stop_loss_pct = self.config['risk_management']['stop_loss_pct']
        if signal == 'buy':
            dist = atr(data, period=atr_period)*stop_loss_pct*2

            # Std_dev to measure distance
            # dist = std_dev(data, period=self.config['strategy']['bollinger_period'])

            # Exit when lost 40% of position size
            # dist = 0.4*data.iloc[-1]['close']
        elif signal == 'sell':
            # lower multiplier for short (higher upside risk)
            dist = atr(data, period=atr_period)*stop_loss_pct*1.5

            # Std_dev to measure distance
            # dist = std_dev(data, period=self.config['strategy']['bollinger_period'])

            # Exit when lost 40% of position size
            # dist = 0.4*data.iloc[-1]['close']

        return dist


    # TODO: include fees, and also price probably isn't correct with last close price (gotta cross bid-ask spread)
    def enter_position(self, signal):
        if signal == 'buy':
            self.pos = 'long'
        elif signal == 'sell':
            self.pos = 'short'

        self.pos_size = self.config['risk_management']['portfolio_risk']*self.env.get_balance()/self.sl_dist(signal)
        trade = self.execute_trade(signal, self.pos_size)
        return trade

    def execute_trade(self, signal, size):
        pair = self.config['trading']['pair']
        trade_price, fees, time = self.env.execute_trade(pair, signal, size)        
        trade = Trade(id=len(self.trades)+1,
                     pair=pair,
                     time=time,
                     size=size,
                     price=trade_price,
                     fees=fees,
                     side=signal)
        
        # Update balance (negative for buy, positive for sell)
        multiplier = -1 if signal == 'buy' else 1

        # just for backtesting envrionment
        self.env.update_balance(multiplier * (trade.size * trade.price) - fees)

        self.trades.append(trade)
        return trade

    def save_trade(self, trade: Trade, filename: str):
        # Convert trade to dict for DataFrame
        trade_dict = {
            'id': trade.id,
            'pair': trade.pair,
            'time': trade.time,
            'size': trade.size,
            'price': trade.price,
            'fees': trade.fees,
            'side': trade.side
        }
        
        # Create DataFrame from trade (square brackets because input expects a list of dictionaries)
        trade_df = pd.DataFrame([trade_dict])
        
        # If file doesn't exist or is empty, create it with headers
        if not os.path.exists(filename) or os.path.getsize(filename) == 0:
            trade_df.to_csv(filename, index=False)
        else:
            # Append without headers if file exists and has content
            trade_df.to_csv(filename, mode='a', header=False, index=False)
